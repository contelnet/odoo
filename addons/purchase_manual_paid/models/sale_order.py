from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_id = fields.Many2one(
        'stock.lot',
        string='Número de Serie',
        help='Selecciona el número de serie exacto que vas a entregar.'
    )