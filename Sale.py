# -*- encoding: utf-8 -*-


import math
from osv import fields,osv
import time
import tools
import ir
import pooler
from tools.translate import _
import decimal_precision as dp


class FiscalDocHeader(osv.osv):
   _inherit = "fiscaldoc.header"
   
   def _totgen_doc(self, cr, uid, ids, field_name, arg, context=None):
       res = super(FiscalDocHeader,self)._totgen_doc(cr,uid,ids,field_name,arg,context)
       if ids:
           for document in self.browse(cr, uid, ids, context=context):
               if document.val_punti_sca:
                   res[document.id]['totale_pagare'] = res[document.id].get('totale_pagare',0) - document.val_punti_sca
       return res       
   
   def _totpunti_doc(self, cr, uid, ids, field_name, arg, context=None):
          res={}
          if ids:
              for document in self.browse(cr,uid,ids):
                res[document.id] = {'punti_caricati':0.0}
                res[document.id]['punti_caricati']= self.pool.get('tabella.punti').calc_punti(cr,uid,[document.id],'fiscaldoc.header',context)
                  
          return res
          

   
   _columns = { 
                'partner_amico_id': fields.many2one('res.partner', 'Amico Presentatore',  required=False),
                'righe_promo': fields.one2many('fiscaldoc.promo', 'name', 'Promo Attive alla Conferma', required=False),
                # 'punti_caricati':fields.float('N. Punti Caricati ',digits_compute=dp.get_precision('Account'),readonly=True),
                'punti_caricati':fields.function(_totpunti_doc, method=True, digits_compute=dp.get_precision('Account'), string='N. Punti Caricati', store=False,multi='sums' ),
                'punti_scaricati':fields.float('N. Punti Scaricati ',digits_compute=dp.get_precision('Account'),readonly=False),               
                'val_punti_sca':fields.float('Valore Punti Scaricati',digits_compute=dp.get_precision('Account'),readonly=True),                
                'totale_saldo_punti': fields.float('Saldo Punti ',digits_compute=dp.get_precision('Account'),readonly=False,help="Saldo Punti Attuale"),
    # fields.related('partner_id', 'totale_saldo_punti', string='Saldo Punti', type='float', relation='res.partner', help="Saldo Punti Attuale"),
                'totale_merce':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Merce', store=True, help="Totale Merce", multi='sums'),
                'totale_netto_merce':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Netto Merce', store=True, help="Totale Merce", multi='sums'),
                'totale_imponibile':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Imponibile', store=True, multi='sums'),
                'totale_imposta':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Imposta', store=True, multi='sums'),
                'totale_documento':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Documento', store=True, multi='sums'),             
                'totale_pagare':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Netto da Pagare', store=True, multi='sums'),                
                }
   
   
   def onchange_partner_id(self, cr, uid, ids, part, context):
          res = super(FiscalDocHeader,self).onchange_partner_id(cr, uid, ids, part, context)
          val = res.get('value',False)
          warning = res.get('warning',False)          
          if res and part:
              data_rif=time.strftime('%Y-%m-%d')
              lista_promo = self.pool.get('promo').lista_attive(cr,uid,part,data_rif,context)
              if lista_promo:
                  righe_promo = []
                  for promo in self.pool.get('promo').browse(cr,uid,lista_promo):
                      righe_promo.append({'promo_id':promo.id,'des_estesa':promo.des_estesa})
                  val['righe_promo']=righe_promo
                  warning = {
                    'title': _('PROMO ATTIVE :'),
                    'message': 'Sono presenti promo per questo tipo di cliente'
                    }
              #import pdb;pdb.set_trace()
              part_obj = self.pool.get('res.partner').browse(cr,uid,part)
              if part_obj:
                  val['totale_saldo_punti'] =  part_obj.totale_saldo_punti
                  
          return {'value': val, 'warning': warning}   
      
   def on_change_scarichi(self, cr, uid, ids, punti_scaricati,partner_id):
        val={}
        warning =''        
        if partner_id:
            part = self.pool.get('res.partner').browse(cr,uid,partner_id)
            tabpu = self.pool.get('res.partner').get_tab_punti(cr,uid,partner_id) 
            if tabpu:
             if part.totale_saldo_punti:
                if part.totale_saldo_punti<punti_scaricati:
                    warning =" Non è possibile scaricare + punti di quelli in possesso"
                    val['punti_scaricati']=0
                    val['val_punti_sca']=0.0
                else:
                    val['val_punti_sca']=tabpu.rapporto * punti_scaricati
        else:
                    val['punti_scaricati']=0
                    val['val_punti_sca']=0.0
                    
        
        return {'value':val,'warning':warning}
   
   def write(self, cr, uid, ids, vals, context=None):
       res = super(FiscalDocHeader,self).write(cr,uid,ids,vals,context)
       if res:
           if ids:
               #ok = self.pool.get('tabella.punti').calc_punti(cr,uid,ids,'fiscaldoc.header',context)
               ok = self.pool.get('promo').calcoli_promo(cr,uid,ids,'fiscaldoc.header',context)
       return res       
   
   def create(self, cr, uid, vals, context=None):
       res = super(FiscalDocHeader,self).create(cr,uid,vals,context)
       if res:
           #ok = self.pool.get('tabella.punti').calc_punti(cr,uid,[res],'fiscaldoc.header',context)
           ok = self.pool.get('promo').calcoli_promo(cr,uid,[res],'fiscaldoc.header',context)
       return res
   
FiscalDocHeader()

class FiscalDocRighe(osv.osv):
   _inherit = "fiscaldoc.righe"
   
   _columns = {
               'promo_id':fields.many2one('promo', 'Promozione Utilizzata', required=False),
               }
   
   def cerca_promo(self,cr, uid, ids, product_id, listino_id, qty, partner_id, data_doc, uom,v,context):
       if v:
            #import pdb;pdb.set_trace()
            product_prezzo_unitario = v.get('product_prezzo_unitario',False)
            discount_riga = v.get('discount_riga',False)
            sconti_riga = v.get('sconti_riga',False)            
            cerca = [('da_data','<=',data_doc),('a_data','>=',data_doc),('promo_qt_cat','=',False),('promo_totale','=',False),('sconto_totale','=',False)]
            ids_promo = self.pool.get('promo').search(cr,uid,cerca)
            if ids_promo:
                # ha trovato promo attive definisce il listino
                list = self.pool.get('product.pricelist').browse(cr,uid,listino_id)
                if list.name[:1] == "1": # prezzo al pubblico
                    flg_riv = False
                else: # listino rivenditore
                    flg_riv = True
                for promo in self.pool.get('promo').browse(cr,uid,ids_promo):
                    for riga in promo.righe_promo:
                        product = self.pool.get('product.product').browse(cr,uid,product_id)
                        if riga.categ_id:
                            # legge solo uno sconto aggiuntivo se è uguale
                                if not riga.qta_mov or riga.qta_mov == 0: 
                                    # qta vuota quindi forza il prezzo e/o lo sconto
                                    if flg_riv: # rivenditore
                                        if riga.sconto_al_riv:
                                            discount_riga = riga.sconto_al_riv
                                            sconti_riga=False
                                    else: # utente finale
                                        if riga.sconto_al_pubb:
                                            discount_riga = riga.sconto_al_pubb
                                            sconti_riga=False
                                else:
                                    # è un ragionamento sulla qta 
                                    if qty >= riga.qta_mov: # va applicato lo sconto
                                     if flg_riv: # rivenditore
                                        if riga.sconto_al_riv:
                                            discount_riga = riga.sconto_al_riv
                                            sconti_riga=False
                                     else: # utente finale
                                        if riga.sconto_al_pubb:
                                            discount_riga = riga.sconto_al_pubb
                                            sconti_riga=False
                                            
                        if riga.product_id:
                            # qui può anche ragionare sulla qta
                            if riga.product_id.id == product_id: # è l'articolo in questione
                                if not riga.qta_mov or riga.qta_mov == 0: 
                                    # qta vuota quindi forza il prezzo e/o lo sconto
                                    if flg_riv: # rivenditore
                                        if riga.netto_riv:
                                            product_prezzo_unitario = riga.netto_riv
                                        if riga.sconto_al_riv:
                                            discount_riga = riga.sconto_al_riv
                                            sconti_riga=False
                                    else: # utente finale
                                        if riga.netto_pubb:
                                            product_prezzo_unitario = riga.netto_pubb
                                        if riga.sconto_al_pubb:
                                            discount_riga = riga.sconto_al_pubb
                                            sconti_riga=False
                                else:
                                    # è un ragionamento sulla qta 
                                    if qty >= riga.qta_mov: # va applicato lo sconto
                                     if flg_riv: # rivenditore
                                        if riga.netto_riv:
                                            product_prezzo_unitario = riga.netto_riv
                                        if riga.sconto_al_riv:
                                            discount_riga = riga.sconto_al_riv
                                            sconti_riga=False
                                     else: # utente finale
                                        if riga.netto_pubb:
                                            product_prezzo_unitario = riga.netto_pubb
                                        if riga.sconto_al_pubb:
                                            discount_riga = riga.sconto_al_pubb
                                            sconti_riga=False
            v['product_prezzo_unitario'] = product_prezzo_unitario
            v['discount_riga'] =discount_riga
            v['sconti_riga'] = sconti_riga
            v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga']) 
            v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto']) 
       return v
   
   def onchange_articolo(self, cr, uid, ids,product_id, listino_id, qty, partner_id, data_doc, uom,context):
    v = {}
    domain={}
    warning = {}
    #import pdb;pdb.set_trace()
    if context:
#        location = context
#        context={'location':location}
         pass
    res = super(FiscalDocRighe,self).onchange_articolo(cr, uid, ids, product_id, listino_id, qty, partner_id, data_doc, uom,context)
    if res:
        #import pdb;pdb.set_trace()
        v = res.get('value',False)
        domain = res.get('domain',False)
        warning = res.get('warning',False)
        if not warning and v:
            message = self.pool.get('promo').promo_articolo_attive(cr,uid,partner_id,data_doc,product_id,context)
            if message: 
                warning = {
                    'title': _('PROMO ATTIVE :'),
                    'message': message
                    }
                
    return {'value': v, 'domain': domain, 'warning': warning}

   def on_change_qty(self,cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc,context):

    v = {}
    domain={}
    warning = {}
    #import pdb;pdb.set_trace()
    if context:
        pass
    res = super(FiscalDocRighe,self).on_change_qty(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc,context)
    if res:
        v = res.get('value',False)
        domain = res.get('domain',False)
        warning = res.get('warning',False)
            
    return {'value': v, 'domain': domain, 'warning': warning}


FiscalDocRighe()

class sale_order(osv.osv):
    _inherit = "sale.order"   

    def _totpunti_doc(self, cr, uid, ids, field_name, arg, context=None):
          res={}
          if ids:
              for document in self.browse(cr,uid,ids):
                res[document.id] = {'punti_caricati':0.0}
                res[document.id]['punti_caricati']= self.pool.get('tabella.punti').calc_punti(cr,uid,[document.id],'sale.order',context)
                  
          return res
    
    _columns = {
                'righe_promo': fields.one2many('sale.order.promo', 'name', 'Promo Attive alla Conferma', required=False),
                'punti_caricati':fields.function(_totpunti_doc, method=True, digits_compute=dp.get_precision('Account'), string='N. Punti Caricati', store=False,multi='sums' ),
                'punti_scaricati':fields.float('N. Punti Scaricati ',digits_compute=dp.get_precision('Account'),readonly=True),
                'val_punti_sca':fields.float('Valore Punti Scaricati',digits_compute=dp.get_precision('Account'),readonly=True),   
                'totale_saldo_punti': fields.related('partner_id', 'totale_saldo_punti', string='Saldo Punti', type='float', relation='res.partner', help="Saldo Punti Attuale"),                             
                }
    
    
    
    def write(self, cr, uid, ids, vals, context=None):
       res = super(sale_order,self).write(cr,uid,ids,vals,context)
       if res:
           if ids:
               #ok = self.pool.get('tabella.punti').calc_punti(cr,uid,ids,'sale_order',context)
               ok = self.pool.get('promo').calcoli_promo(cr,uid,ids,'sale.order',context)
               pass
       return res       
   
    def create(self, cr, uid, vals, context=None):
       res = super(sale_order,self).create(cr,uid,vals,context)
       if res:
           #ok = self.pool.get('tabella.punti').calc_punti(cr,uid,[res],'sale_order',context)
           ok = self.pool.get('promo').calcoli_promo(cr,uid,[res],'sale.order',context)
           pass
       return res
   
    def onchange_partner_id(self, cr, uid, ids, part):
        context = False
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False, 'payment_term': False, 'fiscal_position': False}}

        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['delivery', 'invoice', 'contact'])
        part = self.pool.get('res.partner').browse(cr, uid, part)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
        }
        if pricelist:
            val['pricelist_id'] = pricelist
            
        warning =False 
        if  part:
              data_rif=time.strftime('%Y-%m-%d')
              lista_promo = self.pool.get('promo').lista_attive(cr,uid,part,data_rif,context)
              if lista_promo:
                  righe_promo = []
                  for promo in self.pool.get('promo').browse(cr,uid,lista_promo):
                      righe_promo.append({'promo_id':promo.id,'des_estesa':promo.des_estesa})
                  val['righe_promo']=righe_promo
                  warning = {
                    'title': _('PROMO ATTIVE :'),
                    'message': 'Sono presenti promo per questo tipo di cliente'
                    }
              #import pdb;pdb.set_trace()
              part_obj = self.pool.get('res.partner').browse(cr,uid,part)
              if part_obj:
                  val['totale_saldo_punti'] =  part_obj.totale_saldo_punti
            
        return {'value': val,'warning':warning}
   

sale_order()


class sale_order_line(osv.osv):
    _inherit = 'sale.order.line' 
                    #Do not touch _name it must be same as _inherit
                    #_name = 'sale.order.line' 
    _columns = {
               'promo_id':fields.many2one('promo', 'Promozione Utilizzata', required=False),
                }


    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        res = super(sale_order_line,self).product_id_change( cr, uid, ids, pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,lang, update_tax, date_order, packaging, fiscal_position, flag)
        result = res.get('value',False)
        domain = res.get('domain',False)
        warning = res.get('warning',False)
        context = {}
        if not warning and result:
            message = self.pool.get('promo').promo_articolo_attive(cr,uid,partner_id,date_order,product,context)
            if message: 
                warning = {
                    'title': _('PROMO ATTIVE :'),
                    'message': message
                    }


        return {'value': result, 'domain': domain, 'warning': warning}



sale_order_line()

class res_partner_category(osv.osv):
    _inherit = 'res.partner.category'
    _columns = {
                'tab_punti':fields.many2one('tabella.punti', 'Tabella Punti', required=False),
                }
    
res_partner_category()


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _totali_punti(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            #import pdb;pdb.set_trace()
            if ids:
             for partner_id in  ids:
                 cerca = [('partner_id','=',partner_id)]
                 partner = self.pool.get('res.partner').browse(cr,uid,partner_id)
                 #,('tipo_documento','<>','DT'),('tipo_documento','<>','PF')
                 ids_docs = self.pool.get('fiscaldoc.header').search(cr,uid,cerca)
                 if ids_docs:
                     res[partner_id] = { 'totale_carichi_punti': 0,'totale_scarichi_punti': 0,'totale_saldo_punti': 0}                     
                     totale_carichi_punti = 0
                     totale_scarichi_punti=0                     
                     for doc in self.pool.get('fiscaldoc.header').browse(cr,uid,ids_docs,context):
                         if doc.tipo_doc.tipo_documento<>'DT' and doc.tipo_doc.tipo_documento<>'PF':      
                             totale_carichi_punti += doc.punti_caricati
                             totale_scarichi_punti += doc.punti_scaricati
                     res[partner_id]['totale_carichi_punti'] = totale_carichi_punti
                     res[partner_id]['totale_scarichi_punti'] = totale_scarichi_punti
                     res[partner_id]['totale_saldo_punti'] = partner.saldo_iniziale_punti + res[partner_id]['totale_carichi_punti']-res[partner_id]['totale_scarichi_punti']
                 else:
                    res[partner_id] = { 'totale_carichi_punti': 0,'totale_scarichi_punti': 0,'totale_saldo_punti': 0}
            return res
        
    def get_tab_punti(self,cr,uid,ids,context=None):
            #import pdb;pdb.set_trace()
            res= False
            if ids:
                if type(ids)==type([]):
                    part = self.browse(cr,uid,ids)[0]
                else:
                    part = self.browse(cr,uid,ids)                
                if part.tab_punti:
                           res = part.tab_punti
                else:
                    if part.category_id:
                        res = part.category_id[0].tab_punti
            return res
    
    _columns = {
                'tab_punti':fields.many2one('tabella.punti', 'Tabella Punti', required=False), 
                'saldo_iniziale_punti':fields.float('Saldo Iniziale Punti ',digits_compute=dp.get_precision('Account'),readonly=False),  
                'totale_carichi_punti':fields.function(_totali_punti, method=True, digits_compute=dp.get_precision('Account'), string='Totale Carico Punti', store=False, multi='sums'),
                'totale_scarichi_punti': fields.function(_totali_punti, method=True, digits_compute=dp.get_precision('Account'), string='Totale Scarico Punti', store=False, multi='sums'),
                'totale_saldo_punti': fields.function(_totali_punti, method=True, digits_compute=dp.get_precision('Account'), string='Saldo Punti', store=False, multi='sums'),
                
                }

res_partner()


class pos_order(osv.osv):
    _inherit = "pos.order"

    def _totpunti_doc(self, cr, uid, ids, field_name, arg, context=None):
          res={}
          if ids:
              for document in self.browse(cr,uid,ids):
                res[document.id] = {'punti_caricati':0.0}
                res[document.id]['punti_caricati']= self.pool.get('tabella.punti').calc_punti(cr,uid,[document.id],'pos.order',context)
                  
          return res



    _columns = {
                'righe_promo': fields.one2many('pos.order.promo', 'name', 'Promo Attive alla Conferma', required=False),
                'punti_caricati':fields.function(_totpunti_doc, method=True, digits_compute=dp.get_precision('Account'), string='N. Punti Caricati', store=False,multi='sums' ),
                'punti_scaricati':fields.float('N. Punti Scaricati ',digits_compute=dp.get_precision('Account'),readonly=True),
                'val_punti_sca':fields.float('Valore Punti Scaricati',digits_compute=dp.get_precision('Account'),readonly=True),   
                'totale_saldo_punti': fields.related('partner_id', 'totale_saldo_punti', string='Saldo Punti', type='float', relation='res.partner', help="Saldo Punti Attuale"),                             
                }


pos_order()
