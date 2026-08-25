from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_manually_paid = fields.Boolean(
        string="¿Pagado?",
        help="Marca manualmente si ya has pagado este pedido.",
        default=False,
        tracking=True
    )