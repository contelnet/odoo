# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.mail_plugin.controllers import mail_plugin


class MailPluginController(mail_plugin.MailPluginController):

    def _fetch_partner_tickets(self, partner, limit=5, offset=0):
        Ticket = request.env['helpdesk.ticket']
        commercial_partner = partner.commercial_partner_id or partner
        domain = ['|', ('partner_id', '=', partner.id), ('customer_id', '=', commercial_partner.id)]
        tickets = Ticket.search(domain, offset=offset, limit=limit, order='priority desc, id desc')
        return [
            {
                'ticket_id': ticket.id,
                'number': ticket.number,
                'name': ticket.name,
                'team_name': ticket.team_id.name,
                'stage_name': ticket.stage_id.name,
                'priority': ticket.priority,
            }
            for ticket in tickets
        ]

    def _get_contact_data(self, partner):
        contact_values = super()._get_contact_data(partner)

        can_read_tickets = request.env['helpdesk.ticket'].has_access('read')
        can_create_tickets = request.env['helpdesk.ticket'].has_access('create')
        can_read_teams = request.env['helpdesk.ticket.team'].has_access('read')

        if not can_read_tickets:
            return contact_values

        if not partner:
            contact_values['tickets'] = []
        else:
            contact_values['tickets'] = self._fetch_partner_tickets(partner)

        contact_values['can_create_helpdesk_ticket'] = can_create_tickets
        contact_values['can_select_helpdesk_team'] = can_read_teams
        return contact_values

    def _mail_content_logging_models_whitelist(self):
        models_whitelist = super()._mail_content_logging_models_whitelist()
        if not request.env['helpdesk.ticket'].has_access('write'):
            return models_whitelist
        return models_whitelist + ['helpdesk.ticket']

    def _translation_modules_whitelist(self):
        modules_whitelist = super()._translation_modules_whitelist()
        if not request.env['helpdesk.ticket'].has_access('read'):
            return modules_whitelist
        return modules_whitelist + ['helpdesk_mail_plugin']
