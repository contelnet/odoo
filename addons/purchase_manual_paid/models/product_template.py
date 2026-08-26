from odoo import models, fields, api

# ---------------------------------------------------------
# 1. PLANTILLA DE PRODUCTO (Lo que ya tenías)
# ---------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    related_product_ids = fields.Many2many(
        'product.template',
        'product_rel_rel',
        'dest_id', 'src_id',
        string='Productos relacionados / Compatibles'
    )

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permite buscar por el nombre del producto principal, referencia o productos relacionados.
        """
        domain = domain or []
        if name:
            # Buscamos productos cuyos productos relacionados coincidan
            related_products = self.search([('related_product_ids.name', operator, name)])
            
            # Sintaxis correcta de Odoo para OR con 3 condiciones ('|' repetido)
            search_domain = [
                '|', '|',
                ('name', operator, name),
                ('default_code', operator, name),
                ('id', 'in', related_products.ids)
            ]
            domain = search_domain + domain
            
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

# ---------------------------------------------------------
# 2. TABLA PERSONALIZADA DE SERIALES (El puente hacia Inventario)
# ---------------------------------------------------------
class ProductTemplateSerialNumber(models.Model):
    _inherit = 'product.template.serial.number'

    @api.model_create_multi
    def create(self, vals_list):
        # 1. Creamos el registro en tu pestaña personalizada
        records = super().create(vals_list)
        
        # 2. Hacemos que viaje a la tabla oficial de Odoo (stock.lot)
        StockLot = self.env['stock.lot']
        for rec in records:
            # Buscamos la variante del producto
            product = rec.product_tmpl_id.product_variant_id
            if product and rec.name:
                existe = StockLot.search([
                    ('name', '=', rec.name), 
                    ('product_id', '=', product.id)
                ], limit=1)
                
                if not existe:
                    StockLot.create({
                        'name': rec.name,
                        'product_id': product.id,
                        'company_id': self.env.company.id,
                    })
        return records

    def unlink(self):
        # Si lo borras de tu pestaña, intentamos borrarlo de la tabla oficial
        StockLot = self.env['stock.lot']
        for rec in self:
            product = rec.product_tmpl_id.product_variant_id
            if product and rec.name:
                lot = StockLot.search([
                    ('name', '=', rec.name), 
                    ('product_id', '=', product.id)
                ], limit=1)
                if lot:
                    try:
                        lot.unlink()
                    except Exception:
                        # Si ya está usado en una venta/albarán, Odoo bloqueará el borrado para protegerte
                        pass 
        return super().unlink()