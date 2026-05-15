# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon, mock_auth_method_outlook


class TestHelpdeskMailPluginController(TestMailPluginControllerCommon):
    def setUp(self):
        super().setUp()
        self.helpdesk_user = mail_new_test_user(
            self.env,
            login='helpdesk_employee',
            groups='base.group_user,base.group_partner_manager,helpdesk_mgmt.group_helpdesk_user',
        )
        self.team = self.env['helpdesk.ticket.team'].with_user(self.helpdesk_user).create({
            'name': 'Soporte Outlook',
            'user_ids': [(6, 0, [self.helpdesk_user.id])],
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Cliente Outlook',
            'email': 'cliente@example.com',
        })

    @mock_auth_method_outlook('helpdesk_employee')
    def test_partner_get_returns_tickets(self):
        self.env['helpdesk.ticket'].with_user(self.helpdesk_user).create({
            'name': 'Ticket desde plugin',
            'partner_id': self.partner.id,
            'customer_id': self.partner.commercial_partner_id.id,
            'team_id': self.team.id,
        })
        data = {
            'id': 0,
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {'email': self.partner.email, 'name': self.partner.name},
        }
        result = self.url_open(
            '/mail_plugin/partner/get',
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'},
        ).json().get('result', {})
        self.assertIn('tickets', result)
        self.assertEqual(len(result['tickets']), 1)
        self.assertTrue(result['can_create_helpdesk_ticket'])

    @mock_auth_method_outlook('helpdesk_employee')
    def test_ticket_create(self):
        data = {
            'id': 0,
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'partner_id': self.partner.id,
                'email_subject': 'Correo desde Outlook',
                'email_body': '<p>Detalle del correo</p>',
                'team_id': self.team.id,
            },
        }
        result = self.url_open(
            '/mail_plugin/ticket/create',
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'},
        ).json().get('result', {})
        self.assertTrue(result.get('ticket_id'))
        ticket = self.env['helpdesk.ticket'].browse(result['ticket_id'])
        self.assertEqual(ticket.partner_id, self.partner)
        self.assertEqual(ticket.team_id, self.team)
        self.assertEqual(ticket.name, 'Correo desde Outlook')

    @mock_auth_method_outlook('helpdesk_employee')
    def test_helpdesk_team_search(self):
        data = {
            'id': 0,
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {'search_term': 'Soporte'},
        }
        result = self.url_open(
            '/mail_plugin/helpdesk/team/search',
            data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'},
        ).json().get('result', [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['team_id'], self.team.id)
