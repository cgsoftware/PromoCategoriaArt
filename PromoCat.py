# -*- encoding: utf-8 -*-

import math
from osv import fields,osv
import time
import tools
import ir
import pooler
from tools.translate import _
import decimal_precision as dp


class promo(osv.osv):
    _name = 'promo'
    _description = 'Promozioni e Offerte' 
    _columns = {
                    'name':fields.char('Codice', size=30 , required=True, readonly=False),
                    'desc_promo': fields.char('Descrizione', size=64, required=False ,readonly=False),
                    'des_estesa': fields.text('Descrizione Estesa '),                  
                    'da_data': fields.date('Da Data'),                    
                    'a_data': fields.date('A Data'),
                    'promo_qt_cat':fields.boolean('Promo Qta Categoria', required=False,help='Se attivo la Promozione è ricalcolata a fine Documento per controllare le quantità per categoria'),
                    'promo_totale':fields.boolean('Promo A Totale',help='Se Attivo gestisce uno sconto unico a totale documento'),
                    'sconto_totale': fields.float('Sconto Documento', digits=(9, 3)),
                    'qt_tot_min': fields.float('Quantità Minima ',help="Quantità Minima della promo"),
                    'qt_tot_max': fields.float('Quantità Massima ',help="Quantità  Massima della promo"), 
                    'sc_riv':fields.boolean('Sconti Riv', required=False,help='Se attivo applica anche gli sconti Rivenditori'),
                    'perc_provv':fields.float('Perc. Provvigione Agente', digits=(9, 3)),
                    'rapporto_punti':fields.float('% punti',digits_compute=dp.get_precision('Account'),help="Moltiplicatore Punti,0.5= 50% 2=*2"),
                    'punti_agg':fields.float('Punti Aggiuntivi',digits_compute=dp.get_precision('Account'),help="Aggiunge Punti a quelli calcolati nel documento"),
                    'righe_promo':fields.one2many('promo.dett', 'name', 'Dettaglio Promo', required=False),
                    'righe_partner_cat':fields.many2many('res.partner.category', 'promo_category_rel', 'promo_id', 'righe_partner_cat', 'Lista Categorie Partner', required=False, help='Categorie a cui applicare la promo, se vuoto = Tutti'), 
                                   
                    }    
    
    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','desc_promo'], context, load='_classic_write')
        return [(x['id'], (x['name'] and (x['name'] + ' - ') or '') + x['desc_promo']) \
                for x in reads]

    def lista_attive(self,cr,uid,partner,data_rif,context):
        # lista promo attive alla data per la categoria partner
        #import pdb;pdb.set_trace()
        lista= []
        partner_obj = self.pool.get('res.partner').browse(cr,uid,partner)
        cerca = [('da_data','<=',data_rif),('a_data','>=',data_rif)]
        ids_promo = self.search(cr,uid,cerca)
        if ids_promo:
            if partner_obj.category_id:
                #import pdb;pdb.set_trace()
                for promo_obj in self.browse(cr,uid,ids_promo):
                    if promo_obj.righe_partner_cat: 
                      for cat_pat_id in partner_obj.category_id:
                          for cat_pro_id in promo_obj.righe_partner_cat:
                              if cat_pat_id.id==cat_pro_id.id:
                                  lista.append(promo_obj.id)
                    else:
                        lista.append(promo_obj.id)                        
            else:
                lista=ids_promo
                
   
        return lista
    
    def promo_articolo_attive(self,cr,uid,partner,data_rif,product_id,context):
        #import pdb;pdb.set_trace()
        lst_promo = self.lista_attive(cr, uid, partner, data_rif, context)
        list=[]
        warning = ""
        #import pdb;pdb.set_trace()
        if lst_promo and product_id:
            product_obj = self.pool.get('product.product').browse(cr,uid,product_id)
            for promo in self.browse(cr,uid,lst_promo):
                for riga_pro in promo.righe_promo:
                    #cicla sulle righe promo per verificare se è interessato  nella categoria o sull' articolo
                    #import pdb;pdb.set_trace()
                    if (riga_pro.categ_id): # una riga di solo categoria
                        if riga_pro.categ_id.id == product_obj.categ_id.id:
                            list.append(riga_pro.name.id)                            
                    else:
                        if riga_pro.product_id: # è una riga di articolo diretto
                            if riga_pro.product_id.id == product_obj.id:            
                                list.append(riga_pro.name.id)
            if list: # ha trovato delle promo che interessano in qualche modo l'articolo
                            # ora crea un campo testo da passare al warning da visualizzare semplicemente
                   # warning += 'PROMO ATTIVE : /n'
                   for promo in self.browse(cr,uid,list):
                       warning += promo.name+':'
                       warning += promo.des_estesa+''                    
        return warning

    def verifica_marchio(self,cr,uid,artid,marchio_id):
        if artid and marchio_id:
            ok = False
            if self.pool.get('product.compatibili').search(cr,uid,[('product_id','=',artid),('marchio_sta','=',marchio_id)]):
                ok= True
        return ok
    
    def check_promo(self,cr,uid,model,promo,riga_art):
        #import pdb;pdb.set_trace()
        # cicla sulle righe della promo per verifcare se l'articolo va preso in considerazione nella promo
        if promo.righe_promo:
            for riga_promo in  promo.righe_promo:
                if riga_promo.product_id:
                  if ((riga_promo.qta_mov_min<=riga_art.product_uom_qty and 
                       (riga_promo.qta_mov_max>=riga_art.product_uom_qty or riga_promo.qta_mov_max) and riga_promo.flag_art)
                       or not riga_promo.flag_art ):
                    # Ha verificato prima se la qta è regolare e poi fa il resto dei controlli
                    if riga_promo.product_id.id==riga_art.product_id.id:
                        # è una promo del singolo articolo
                        # return {'promo_riga_id':riga_promo.id,'riga_doc_id':riga_art.id}                        
                            return {'promo_riga':riga_promo,'riga_doc':riga_art}
                if riga_promo.categ_id:
                        if riga_promo.marchio_id:
                            # deve verificare se l'articolo ha quel marchio nei compatibili
                            if riga_promo.categ_id.id==riga_art.product_id.categ_id.id and self.verifica_marchio(cr, uid, riga_art.product_id.id, riga_promo.marchio_id.id):                                
                                    return {'promo_riga':riga_promo,'riga_doc':riga_art}
                        else:
                            if riga_promo.categ_id.id==riga_art.product_id.categ_id.id:                                
                                    return {'promo_riga':riga_promo,'riga_doc':riga_art}
                else:
                    if riga_promo.marchio_id:
                        if  self.verifica_marchio(cr, uid, riga_art.product_id.id, riga_promo.marchio_id.id):
                            return {'promo_riga':riga_promo,'riga_doc':riga_art}  
        return False
    
    def calcoli_promo(self,cr,uid,ids_doc,model,context=None):
        #import pdb;pdb.set_trace()
        if ids_doc:
            for doc in self.pool.get(model).browse(cr,uid,ids_doc):
                if doc.righe_promo:
                    for doc_riga_promo in  doc.righe_promo:
                        if doc_riga_promo.utilizza:
                            # nella lista promo ne trova una attiva ora deve
                            # verificare i vincoli della promo ed applicarli se attivi alrimenti torvare il modo di segnalare senza errore 
                            # la non rispondenza alla promo.
                            lst_art_promo = []
                            totmin = doc_riga_promo.promo_id.qt_tot_min
                            totmax = doc_riga_promo.promo_id.qt_tot_max
                            ok_promo = False
                            #import pdb;pdb.set_trace()
                            promo = doc_riga_promo.promo_id
                            if model == 'fiscaldoc.header':
                              for riga_art in doc.righe_articoli:
                                lst_art_promo.append(self.check_promo(cr, uid, model, promo, riga_art))
                            if model == 'sale.order':
                              for riga_art in doc.order_line:
                                lst_art_promo.append(self.check_promo(cr, uid, model, promo, riga_art))
                            # a questo punto ho l'elenco delle righe che devono essere tenute in considerazione per il calcoli delle qta da verificare
                            totqta=0
                            if lst_art_promo:
                                lst_tot_cat={}
                                # ora calcola i totali qta del documento ed i totali qta per categoria se serve
                                for ls_promo in lst_art_promo:
                                    if ls_promo:
                                        # è una riga utile
                                        promo_rig = ls_promo.get('promo_riga',False)
                                        rig_art = ls_promo.get('riga_doc',False)
                                        if promo_rig.flag_art:
                                            # controllo sulla riga xchè  è sulla articolo
                                            totqta+=rig_art.product_uom_qty
                                        else:
                                            #deve ragionare a totale marchio o a totale categoria o entrambe non sul singolo articolo
                                            if promo_rig.categ_id and promo_rig.marchio_id:
                                                code = 'c'+str(promo_rig.categ_id.id)+'-'+'m'+str(promo_rig.marchio_id.id)
                                            if promo_rig.categ_id:
                                                code = 'c'+str(promo_rig.categ_id.id)
                                            if promo_rig.marchio_id:
                                                code = 'm'+str(promo_rig.marchio_id.id)
                                            qta_dic = lst_tot_cat.get(code,False)
                                            if qta_dic:
                                                # è gia passato una volta 
                                                totqta+=rig_art.product_uom_qty
                                                qta_dic['totqta']+= rig_art.product_uom_qty
                                                qta_dic['list_rig'].append(rig_art)
                                                lst_tot_cat[code] = qta_dic
                                            else:
                                                # è la prima volta
                                                qta_dic = {
                                                           'promo_rig':promo_rig,
                                                           'list_rig':[rig_art],
                                                           'totqta':rig_art.product_uom_qty
                                                           }
                                                lst_tot_cat[code] = qta_dic
                                                totqta+=rig_art.product_uom_qty
                                    else:
                                        # era una riga scartata per l'offerta
                                        pass
                                #ora faccio prima il controllo sul totale qta generale della promo
                                if totmin<= totqta and (totmax>=totqta or totmax==0 or totmax==False):
                                    # la promo è ok sui totali generali
                                    pass #TO DO SOMETHING ?
                                    ok_promo= True
                                # ora controllo se i totali di categoria sono rispettati
                                if lst_tot_cat:
                                    for qta_dic in lst_tot_cat.values():
                                        #import pdb;pdb.set_trace()
                                        if qta_dic['totqta']>= qta_dic['promo_rig'].qta_mov_min and (qta_dic['totqta']<=qta_dic['promo_rig'].qta_mov_max or qta_dic['promo_rig'].qta_mov_max==0):
                                            # ok la promo è risteppata
                                            pass
                                            ok_promo= True
                                        else:
                                            pass
                                            ok_promo= False
                                           # la promo non è ok
                            if ok_promo:
                                # la promo va applicata
                                for ls_promo in lst_art_promo: # cicla sulle righe della promo e scrive ciò che deve visto che tutto è ok
                                    if ls_promo:
                                        promo_rig = ls_promo.get('promo_riga',False)
                                        rig_art = ls_promo.get('riga_doc',False)                                        
                                        if model == 'fiscaldoc.header':
                                            riga_obj= self.pool.get('fiscaldoc.righe')
                                            dativar={}
                                            if  "1" in rig_art.name.listino_id.name:
                                                #listino al pubblico
                                                if promo_rig.netto_pubb:
                                                    dativar['product_prezzo_unitario']= promo_rig.netto_pubb
                                                else:
                                                    dativar['product_prezzo_unitario']= rig_art.product_prezzo_unitario
                                                dativar['sconti_riga']=""
                                                if promo_rig.sconto_al_pubb:
                                                    dativar['discount_riga']= promo_rig.sconto_al_pubb
                                                else:
                                                    dativar['discount_riga']= rig_art.discount_riga
                                                dativar['prezzo_netto']= riga_obj.calcola_netto(cr, uid, [rig_art.id],dativar['product_prezzo_unitario'], dativar['discount_riga'])
                                                dativar['totale_riga']=dativar['prezzo_netto']*rig_art.product_uom_qty
                                            else:
                                                # listino rivenditore
                                                if promo_rig.netto_riv:
                                                    dativar['product_prezzo_unitario']= promo_rig.netto_riv
                                                else:
                                                    dativar['product_prezzo_unitario']= rig_art.product_prezzo_unitario
                                                dativar['sconti_riga']=""
                                                if promo_rig.sconto_al_riv:
                                                    dativar['discount_riga']= promo_rig.sconto_al_riv
                                                else:
                                                    dativar['discount_riga']= rig_art.discount_riga
                                                dativar['prezzo_netto']= riga_obj.calcola_netto(cr, uid, [rig_art.id], dativar['product_prezzo_unitario'], dativar['discount_riga'])
                                                dativar['totale_riga']=dativar['prezzo_netto']*rig_art.product_uom_qty
                                            if dativar:
                                                ok  = riga_obj.write(cr,uid,[rig_art.id],dativar)
                                        else:
                                            #import pdb;pdb.set_trace() 
                                            #ordini di vendita
                                            riga_obj= self.pool.get('sale.order.line')
                                            dativar={}
                                            if  "1" in rig_art.order_id.pricelist_id.name:
                                                #listino al pubblico
                                                if promo_rig.netto_pubb:
                                                    dativar['price_unit']= promo_rig.netto_pubb
                                                else:
                                                    dativar['price_unit']= rig_art.price_unit
                                                
                                                if promo_rig.sconto_al_pubb:
                                                    dativar['discount']= promo_rig.sconto_al_pubb
                                                else:
                                                    dativar['discount']= rig_art.discount
                                            else:
                                                # listino rivenditore
                                                if promo_rig.netto_riv:
                                                    dativar['price_unit']= promo_rig.netto_riv
                                                else:
                                                    dativar['price_unit']= rig_art.price_unit
                                                
                                                if promo_rig.sconto_al_riv:
                                                    dativar['discount']= promo_rig.sconto_al_riv
                                                else:
                                                    dativar['discount']= rig_art.discount
                                            if dativar:
                                                ok  = riga_obj.write(cr,uid,[rig_art.id],dativar)
                                            
                            else:
                                # deve lanciare una raise ? o cosa ? ma deve comunque continuare il lavoro che faceva
                                pass
                                    
        return True
    
promo()

class promo_cat_dett(osv.osv):
    _name = 'promo.dett'
    _description = 'Promozioni e Offerte dettaglio' 
    _columns = {
                'name':fields.many2one('promo', 'Promo di Appartenenza', required=True), 
                'categ_id':fields.many2one('product.category', 'Categoria', required=False),
                'marchio_id':fields.many2one('marchio.comp', 'Marchio Compatibile', required=False),
                'flag_art':fields.boolean('Su Articolo', required=False, help="Se attivo la promo è attiva su tutti gli articoli che appartengono alla categoria, altrimenti il calcolo è a totale documento su tutte le righe che appartendono alla categoria"),
                'product_id':fields.many2one('product.product', 'Articolo', required=False),                 
                'qta_mov_min': fields.float('Qta Minima', digits=(16,2), help="Se zero non c'è controllo sulla qta"), 
                'qta_mov_max': fields.float('Qta Massima', digits=(16,2), help="Se zero non c'è controllo sulla qta"),
                'listino_pubb':fields.float('Listino Pubblico',digits_compute=dp.get_precision('Account')),
                'netto_pubb':fields.float('Prezzo netto al Pubblico',digits_compute=dp.get_precision('Account')),
                'listino_riv':fields.float('Listino Rivenditore',digits_compute=dp.get_precision('Account')),
                'netto_riv':fields.float('Prezzo netto al Rivenditore',digits_compute=dp.get_precision('Account')),     
                'sconto_al_pubb':fields.float('Sconto al Pubblico', digits=(9, 3)),
                'sconto_al_riv':fields.float('Sconto al Rivenditore', digits=(9, 3)),
                }
    
    def on_change_articolo(self,cr, uid, ids, product_id,context):
        v = {}
        domain={}
        warning = {}
        partner_id = False
        #import pdb;pdb.set_trace()
        if context:
            cerca = [('name','ilike','1')]
            listino_id = self.pool.get('product.pricelist').search(cr,uid,cerca)
            if listino_id:       
                price = self.pool.get('product.pricelist').price_get(cr, uid, listino_id,product_id,1.0 , partner_id)[listino_id[0]]
                v['listino_pubb']= price                
            else:
                
                warning = {
                    'title': _('Errore Listino :'),
                    'message': "Listino 1 non trovato"
                    }

            cerca = [('name','ilike','2')]
            listino_id = self.pool.get('product.pricelist').search(cr,uid,cerca)
            if listino_id:       
                price = self.pool.get('product.pricelist').price_get(cr, uid, listino_id,product_id,1.0 , partner_id)[listino_id[0]]
                v['listino_riv']= price                
            else:
                
                  warning = {
                    'title': _('Errore Listino :'),
                    'message': "Listino 2 non trovato"
                    }
            
        return {'value': v, 'domain': domain, 'warning': warning}

promo_cat_dett()


class tabella_punti(osv.osv):
    _name = 'tabella.punti'
    _description = 'Definizione Calcolo Punti' 
    _columns = {
                    'name':fields.char('Codice', size=15 , required=True, readonly=False),
                    'desc_calcolo': fields.char('Descrizione', size=64, required=False ,readonly=False), 
                    'base_calc':fields.selection([
                        ('tot','Sul Totale Documento'),
                        ('prn','Prezzo Netto'),
                        ('tor','Totale di Riga'),
                        ('prl','Prezzo di Listino')
                        ],    'Base di Calcolo Punti', select=True, readonly=False),
                'python_code':fields.text('Python Code/Formula Calcolo', help="""Formula di calcolo, ci sono 2 variabili:
                                                                            base= Base di Calcolo  
                                                                            qta= Quantità Articolo  sulla riga
                                                                            è possibile inserire codice python con controlli      
                                                                            Esempio semplice :
                                                                            N. punti = qta*base*0.10  un punto = al 10% del valore venduto di riga.
                                                                             """),
                'rapporto':fields.float('Rapporto Valore',digits_compute=dp.get_precision('Account'),help=" se 1 un punto = 1 euro"),
                'product_id': fields.many2one('product.product', 'Articolo', required=True, ondelete='cascade', help="Articolo servizio per evidenziare lo scarico punti in valore", select=False, domain=[('type','=','service')]),
                'righe_premi':fields.one2many('tabella.punti_premi', 'name', 'Dettaglio Premi', required=False),
                }
    
    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','desc_calcolo'], context, load='_classic_write')
        return [(x['id'], (x['name'] and (x['name'] + ' - ') or '') + x['desc_calcolo']) \
                for x in reads]
        
    def calc_punti(self,cr,uid,ids_doc,model,context=None):
        numpunti = 0
        if ids_doc:
            for doc in self.pool.get(model).browse(cr,uid,ids_doc):
                tabpu = self.pool.get('res.partner').get_tab_punti(cr,uid,doc.partner_id.id,context)
                if tabpu:
                        #import pdb;pdb.set_trace()                        
                        if tabpu.base_calc == 'tot': # sul totale documento
                            if model == 'fiscaldoc.header':
                                calcolo = tabpu.python_code.replace('base','doc.totale_documento')
                                calcolo = calcolo.replace('qta','1')
                            if model == 'sale.order':
                                calcolo = tabpu.python_code.replace('base','doc.amount_total')
                                calcolo = calcolo.replace('qta','1')
                            if model == 'pos.order':
                                calcolo = tabpu.python_code.replace('base','doc.amount_total')
                                calcolo = calcolo.replace('qta','1')
                                
                        if tabpu.base_calc == 'tor': # sul totale di riga 
                            if model == 'fiscaldoc.header':
                                calcolo = tabpu.python_code.replace('base','riga.totale_riga')
                                calcolo = calcolo.replace('qta','1')
                            if model == 'sale.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_subtotal')
                                calcolo = calcolo.replace('qta','1')
                            if model == 'pos.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_subtotal')
                                calcolo = calcolo.replace('qta','1')
                                
                        if tabpu.base_calc == 'prl': # sul prezzo di listino assegnato 
                            if model == 'fiscaldoc.header':
                                calcolo = tabpu.python_code.replace('base','riga.product_prezzo_unitario')
                                calcolo = calcolo.replace('qta','riga.product_uom_qty')
                            if model == 'sale.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_unit')
                                calcolo = calcolo.replace('qta','riga.product_uom_qty')
                            if model == 'pos.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_unit')
                                calcolo = calcolo.replace('qta','riga.qty')
                                
                        if tabpu.base_calc == 'prn': # sul prezzo prezzo netto di riga 
                            if model == 'fiscaldoc.header':
                                calcolo = tabpu.python_code.replace('base','riga.prezzo_netto')
                                calcolo = calcolo.replace('qta','riga.product_uom_qty')
                            if model == 'sale.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_unit* (1 - (discount or 0.0) / 100.0)')
                                calcolo = calcolo.replace('qta','riga.product_uom_qty')
                            if model == 'pos.order':
                                calcolo = tabpu.python_code.replace('base','riga.price_unit* (1 - (riga.price_ded or 0.0) / 100.0)')
                                calcolo = calcolo.replace('qta','riga.qty')
                                
                        if tabpu.base_calc == 'tot':
                            # non ho bisogno di cliclare sulle righe del documento
                            numpunti = eval(calcolo)
                        else:
                            numpunti = 0
                            if model == 'fiscaldoc.header':
                                for riga in doc.righe_articoli:
                                    numpunti += eval(calcolo)
                            else:
                                for riga in doc.order_line:
                                    numpunti += eval(calcolo)                                
                        if numpunti:
                            pass
                           #import pdb;pdb.set_trace()
                           #self.pool.get(model).write(cr,uid,[doc.id],{'punti_caricati':numpunti})
        return numpunti

        
    
tabella_punti()

class tabella_punti_premi(osv.osv):
    _name = 'tabella.punti_premi'
    _description = 'Definizione Calcolo Punti' 
    _columns = {
                'name':fields.many2one('tabella.punti', 'Testa Tabella', required=True),
                'codice':fields.char('Codice', size=7, required=True, readonly=False),
                'punti': fields.integer('Punti Utlizzo Premio'),
                'valore': fields.float('Valore Premio', digits_compute=dp.get_precision('Account')),
                
                }
        
tabella_punti_premi()

class fiscaldoc_promo(osv.osv):
    _name = 'fiscaldoc.promo'
    _description = 'Promo del Documento' 
    
    _columns = {
                'name': fields.many2one('fiscaldoc.header', 'Numero Documento', required=True, ondelete='cascade', select=True, readonly=True),        
                'promo_id':fields.many2one('promo', 'Promo Utilizzata', required=True), # mettere una domain che controlli la data e che selezioni la categoria cliente e solo le promo a totale
                'des_estesa': fields.text('Descrizione Estesa '),
                'utilizza':fields.boolean('Utilizza', required=False, help="Se attivo la promozione sarà utilizzata"), 
                }

fiscaldoc_promo()

class sale_order_promo(osv.osv):
    _name = 'sale.order.promo'
    _description = 'Promo dell ordine' 
    
    _columns = {
                'name': fields.many2one('sale.order', 'Ordine', required=True, ondelete='cascade', select=True, readonly=True),        
                'promo_id':fields.many2one('promo', 'Promo Utilizzata', required=True), # mettere una domain che controlli la data e che selezioni la categoria cliente e solo le promo a totale
                'des_estesa': fields.text('Descrizione Estesa '),
                'utilizza':fields.boolean('Utilizza', required=False, help="Se attivo la promozione sarà utilizzata"), 
                }

sale_order_promo()


class pos_order_promo(osv.osv):
    _name = 'pos.order.promo'
    _description = 'Promo dell ordine' 
    
    _columns = {
                'name': fields.many2one('pos.order', 'Ordine', required=True, ondelete='cascade', select=True, readonly=True),        
                'promo_id':fields.many2one('promo', 'Promo Utilizzata', required=True), # mettere una domain che controlli la data e che selezioni la categoria cliente e solo le promo a totale
                'des_estesa': fields.text('Descrizione Estesa '),
                'utilizza':fields.boolean('Utilizza', required=False, help="Se attivo la promozione sarà utilizzata"), 
                }

pos_order_promo()

