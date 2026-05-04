# -*- coding: utf-8 -*-

from odoo import models, fields

class OutlookSync(models.Model):
    _name = 'odoo_outlook.outlook_sync'
    _description = 'Outlook Sync'

    server = fields.Char(readonly=True, default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
    database = fields.Char(readonly=True, default=lambda self: self.env.cr.dbname)

    def download_outlook(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_outlook_add_in',
            'target': 'self',
        }

