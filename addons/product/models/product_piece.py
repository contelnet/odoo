from odoo import api, fields, models


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
    display_name = fields.Char(
        string="Nombre para mostrar",
        compute="_compute_display_name",
    )

    @api.depends("name")
    def _compute_display_name(self):
        for piece in self:
            piece.display_name = piece.name or ""
