from odoo import fields, models


class ProductTemplateSerialNumber(models.Model):
    _name = "product.template.serial.number"
    _description = "Product Serial Number"
    _order = "id desc"

    name = fields.Char(string="Numero de serie", required=True)
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Producto",
        required=True,
        ondelete="cascade",
    )
    create_date = fields.Datetime(string="Fecha de alta", readonly=True)

    _sql_constraints = [
        (
            "product_template_serial_unique",
            "unique(product_tmpl_id, name)",
            "El numero de serie ya existe para este producto.",
        )
    ]
