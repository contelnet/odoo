from odoo import http
from odoo.http import request, content_disposition
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
