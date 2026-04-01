from odoo import fields, models


class ProductTemplatePiece(models.Model):
    _name = "product.template.piece"
    _description = "Product Piece"
    _order = "id desc"

    name = fields.Char(string="Pieza", required=True)
    serial_number = fields.Char(string="Numero de serie")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        related="product_tmpl_id.cost_currency_id",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Precio pieza",
        currency_field="currency_id",
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Producto",
        required=True,
        ondelete="cascade",
    )
    create_date = fields.Datetime(string="Fecha de alta", readonly=True)
