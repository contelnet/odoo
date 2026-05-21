from odoo import api, fields, models


class ProductTemplatePiece(models.Model):
    _name = "product.template.piece"
    _description = "Product Piece"
    _order = "id desc"

    name = fields.Char(string="Pieza", required=True)
    piece_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Producto pieza",
        ondelete="set null",
    )
    serial_number = fields.Char(string="Numero de serie")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moneda",
        related="product_tmpl_id.cost_currency_id",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Precio compra",
        currency_field="currency_id",
    )
    sale_price_unit = fields.Monetary(
        string="Precio venta",
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

    @api.depends("name", "piece_product_id", "piece_product_id.display_name")
    def _compute_display_name(self):
        for piece in self:
            piece.display_name = (
                piece.piece_product_id.display_name
                or piece.name
                or ""
            )

    @api.onchange("piece_product_id")
    def _onchange_piece_product_id(self):
        for piece in self:
            if not piece.piece_product_id:
                continue
            piece.name = piece.piece_product_id.display_name or piece.piece_product_id.name
            piece.price_unit = piece.piece_product_id.standard_price or 0.0
            piece.sale_price_unit = piece.piece_product_id.list_price or 0.0
