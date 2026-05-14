from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    has_serial_number = fields.Boolean(
        string="Tiene numero de serie",
        compute="_compute_has_serial_number",
        inverse="_inverse_has_serial_number",
    )

    @api.depends("tracking")
    def _compute_has_serial_number(self):
        for product in self:
            product.has_serial_number = product.tracking == "serial"

    def _inverse_has_serial_number(self):
        for product in self:
            if product.has_serial_number:
                product.is_storable = True
                product.tracking = "serial"
            elif product.tracking == "serial":
                product.tracking = "none"
                product.serial_number_input = False
