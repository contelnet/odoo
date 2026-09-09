from odoo import models, fields

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # Pisamos el campo original para meterle el HTML.
    description = fields.Html(string="Descripción", sanitize=True)