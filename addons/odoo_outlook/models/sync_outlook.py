# -*- coding: utf-8 -*-

import os

from odoo import _, fields, models


class OutlookSync(models.Model):
    _name = 'odoo_outlook.outlook_sync'
    _description = 'Outlook Sync'

    server = fields.Char(readonly=True, default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
    database = fields.Char(readonly=True, default=lambda self: self.env.cr.dbname)
    setup_status_html = fields.Html(compute='_compute_setup_status_html', sanitize=False)
    installer_available = fields.Boolean(compute='_compute_installer_available')

    def _compute_installer_available(self):
        installer_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'bin',
            'OutlookAddInInstaller.exe',
        )
        installer_available = os.path.isfile(installer_path)
        for record in self:
            record.installer_available = installer_available

    def _compute_setup_status_html(self):
        for record in self:
            server = (record.server or '').strip()
            items = []
            if server.startswith('http://localhost') or server.startswith('https://localhost') or '127.0.0.1' in server:
                items.append(
                    _(
                        'La URL actual usa <strong>localhost</strong>. Eso solo sirve si Outlook está instalado en el mismo equipo que Odoo.'
                    )
                )
            else:
                items.append(
                    _(
                        'La URL configurada es apta para un uso profesional siempre que el equipo de Outlook pueda abrirla por red.'
                    )
                )
            if record.installer_available:
                items.append(_('El instalador del complemento está disponible para descarga.'))
            else:
                items.append(_('No se ha encontrado el instalador del complemento en el servidor.'))

            items.append(
                _(
                    'Uso soportado en producción: abrir un correo en Outlook y crear el ticket desde el panel de Odoo. La sincronización antigua de contactos/calendario no es el flujo recomendado.'
                )
            )
            record.setup_status_html = '<ul style="margin: 0; padding-left: 18px;">%s</ul>' % ''.join(
                f'<li>{item}</li>' for item in items
            )

    def download_outlook(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_outlook_add_in',
            'target': 'self',
        }

    def action_test_outlook_setup(self):
        self.ensure_one()
        server = (self.server or '').strip()
        messages = []
        level = 'success'

        if not self.installer_available:
            level = 'danger'
            messages.append(_('No se ha encontrado el instalador del complemento en el servidor.'))

        if server.startswith('http://localhost') or server.startswith('https://localhost') or '127.0.0.1' in server:
            if level != 'danger':
                level = 'warning'
            messages.append(
                _('La URL actual usa localhost. En producción debes usar una IP o dominio accesible desde el equipo de Outlook, salvo que Outlook y Odoo estén en la misma máquina.')
            )
        else:
            messages.append(
                _('La URL configurada parece válida para producción. Comprueba desde el PC de Outlook que puedes abrir %(server)s en el navegador.') % {'server': server or '-'}
            )

        messages.append(
            _('Base de datos a introducir en el complemento: %(database)s') % {'database': self.database or '-'}
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Diagnóstico de Outlook'),
                'message': '\n'.join(messages),
                'type': level,
                'sticky': True,
            },
        }

    def action_open_health_check(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/odoo_outlook/health',
            'target': 'new',
        }

