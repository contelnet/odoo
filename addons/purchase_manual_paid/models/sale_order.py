from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permite buscar presupuestos/pedidos de venta escribiendo el número de serie en la barra de búsqueda.
        """
        domain = domain or []
        if name:
            # Buscamos en las líneas de venta cuyo número de serie (serial_id) coincida con el texto introducido
            lines = self.env['sale.order.line'].search([('serial_id.name', operator, name)])
            order_ids = lines.mapped('order_id').ids
            
            search_domain = [
                '|', '|',
                ('name', operator, name),
                ('client_order_ref', operator, name),
                ('id', 'in', order_ids)
            ]
            domain = search_domain + domain
            
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_id = fields.Many2one(
        'stock.lot',
        string='Número de Serie',
        help='Selecciona el número de serie exacto que vas a entregar.'
    )

    @api.onchange('product_id')
    def _onchange_product_id_serial_domain(self):
        if self.product_id:
            return {'domain': {'serial_id': [('product_id', '=', self.product_id.id)]}}
        return {'domain': {'serial_id': []}}

    def action_open_multi_serial_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Seleccionar números de serie',
            'res_model': 'sale.order.line.serial.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_line_id': self.id,
                'default_product_id': self.product_id.id,
            },
        }