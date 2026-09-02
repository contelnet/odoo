from odoo import models, fields, api
from odoo.exceptions import UserError

# ---------------------------------------------------------
# 1. PLANTILLA DE PRODUCTO
# ---------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    related_product_ids = fields.Many2many(
        'product.template',
        'product_rel_rel',
        'dest_id', 'src_id',
        string='Productos relacionados / Compatibles'
    )
    
    template_serial_ids = fields.One2many(
        'product.template.serial.number',
        'product_tmpl_id',
        string='Seriales del producto'
    )

    # --- NUEVO CAMPO: Ubicación física en el almacén ---
    ubicacion_almacen = fields.Char(
        string="Ubicación",
        help="Ubicación física del producto (Ej: Estantería A, Pasillo 3)"
    )
    # ---------------------------------------------------

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            custom_serials = self.env['product.template.serial.number'].search([('name', operator, name)])
            product_tmpl_ids = custom_serials.mapped('product_tmpl_id').ids

            related_products = self.search([('related_product_ids.name', operator, name)])

            search_domain = [
                '|', '|', '|',
                ('name', operator, name),
                ('default_code', operator, name),
                ('id', 'in', product_tmpl_ids),
                ('id', 'in', related_products.ids),
            ]
            domain = search_domain + domain

        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    # --- NUEVA MAGIA: Anular la validación obligatoria de la casilla ---
    def _check_serial_number(self):
        """
        Sobrescribimos la función original de product_catalog para que 
        no lance el ValidationError al marcar la casilla sin meter serial.
        """
        pass
    # -------------------------------------------------------------------

# ---------------------------------------------------------
# 2. TABLA PERSONALIZADA DE SERIALES (El puente hacia Inventario)
# ---------------------------------------------------------
class ProductTemplateSerialNumber(models.Model):
    _inherit = 'product.template.serial.number'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        StockLot = self.env['stock.lot']
        for rec in records:
            product = rec.product_tmpl_id.product_variant_id
            if not product:
                raise UserError(
                    f"No se pudo sincronizar el serial '{rec.name}': "
                    f"el producto '{rec.product_tmpl_id.name}' no tiene variante disponible."
                )
            if rec.name:
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
            
            # --- NUEVA MAGIA: El chivato del borrado en el historial ---
            if rec.name and rec.product_tmpl_id:
                # Añadidas las comillas simples para que el número quede limpio y destacado
                mensaje = f"🗑️ Aviso del sistema: Se ha eliminado manualmente el número de serie '{rec.name}' de la pestaña de seriales."
                rec.product_tmpl_id.message_post(body=mensaje)
            # -----------------------------------------------------------

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