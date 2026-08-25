from odoo import models, fields, api

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