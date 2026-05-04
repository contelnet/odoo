# -*- coding: utf-8 -*-

from odoo import models, fields

class MailMessage(models.Model):
    _inherit = 'mail.message'

    from_outlook = fields.Boolean(string='Added from Outlook', default=False)