import json
from odoo import http
from odoo.http import content_disposition, request
import os


class OutlookDownload(http.Controller):
    @http.route('/web/binary/download_outlook_add_in', type='http', auth="user")
    def download_outlook_add_in(self, **kw):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        installer_path = os.path.join(dir_path, '..', 'bin', 'OutlookAddInInstaller.exe')
        if not os.path.isfile(installer_path):
            return request.not_found()
        with open(installer_path, 'rb') as installer:
            return request.make_response(
                installer.read(),
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', content_disposition('OutlookAddInInstaller.exe'))]
            )

    @http.route('/odoo_outlook/health', type='http', auth="user")
    def outlook_health(self, **kw):
        payload = {
            'status': 'ok',
            'database': request.db,
            'base_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url') or '',
            'user': request.env.user.login,
            'modules': {
                'odoo_outlook': request.env['ir.module.module'].sudo().search_count([
                    ('name', '=', 'odoo_outlook'), ('state', '=', 'installed')
                ]) > 0,
                'helpdesk_mgmt': request.env['ir.module.module'].sudo().search_count([
                    ('name', '=', 'helpdesk_mgmt'), ('state', '=', 'installed')
                ]) > 0,
                'odoo_outlook_helpdesk_button': request.env['ir.module.module'].sudo().search_count([
                    ('name', '=', 'odoo_outlook_helpdesk_button'), ('state', '=', 'installed')
                ]) > 0,
            },
        }
        return request.make_response(
            json.dumps(payload, indent=2),
            [('Content-Type', 'application/json; charset=utf-8')],
        )
