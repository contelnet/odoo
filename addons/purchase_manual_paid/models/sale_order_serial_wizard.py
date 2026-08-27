from odoo import models, fields, api

class SaleOrderLineSerialWizard(models.TransientModel):
    _name = 'sale.order.line.serial.wizard'
    _description = 'Selector múltiple de números de serie'

    order_line_id = fields.Many2one('sale.order.line', required=True)
    product_id = fields.Many2one('product.product', required=True)
    serial_ids = fields.Many2many(
        'stock.lot',
        string='Números de serie',
        domain="[('product_id', '=', product_id)]",
    )

    def action_confirm(self):
        self.ensure_one()
        line = self.order_line_id
        serials = self.serial_ids

        if not serials:
            return {'type': 'ir.actions.act_window_close'}

        line.write({'serial_id': serials[0].id, 'product_uom_qty': 1})

        for lot in serials[1:]:
            line.copy({
                'order_id': line.order_id.id,
                'serial_id': lot.id,
                'product_uom_qty': 1,
            })

        return {'type': 'ir.actions.act_window_close'}