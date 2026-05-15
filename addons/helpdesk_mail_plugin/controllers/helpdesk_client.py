# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http
from odoo.http import request
from odoo.tools import html2plaintext


class HelpdeskClient(http.Controller):

    def _get_default_team(self):
        user_teams = request.env.user.helpdesk_team_ids.filtered(lambda team: team.active)
        if user_teams:
            return user_teams.sorted(lambda team: (team.sequence, team.id))[:1]
        return request.env['helpdesk.ticket.team'].search([('active', '=', True)], order='sequence, id', limit=1)

    def _prepare_ticket_values(self, partner, email_subject, email_body, team=False):
        channel = request.env.ref('helpdesk_mgmt.helpdesk_ticket_channel_email', raise_if_not_found=False)
        commercial_partner = partner.commercial_partner_id or partner
        subject = html2plaintext(email_subject or '').strip() or _('Ticket for %s', partner.name)
        values = {
            'name': subject,
            'description': email_body,
            'channel_id': channel.id if channel else False,
            'partner_name': partner.name,
            'partner_email': partner.email,
        }
        if partner.is_company:
            values['customer_id'] = commercial_partner.id
        else:
            values['customer_id'] = commercial_partner.id
            values['partner_id'] = partner.id
        if team:
            values['team_id'] = team.id
            if team.company_id:
                values['company_id'] = team.company_id.id
        return values

    def _get_ticket_url(self, ticket):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        return f"{base_url}/web#id={ticket.id}&model=helpdesk.ticket&view_type=form" if base_url else ''

    @http.route('/mail_plugin/helpdesk/team/search', type='json', auth='outlook', cors='*')
    def helpdesk_team_search(self, search_term='', limit=5):
        domain = [('active', '=', True)]
        if search_term:
            domain.append(('name', 'ilike', search_term))
        teams = request.env['helpdesk.ticket.team'].search(domain, limit=limit, order='sequence, id')
        return [
            {
                'team_id': team.id,
                'name': team.complete_name,
                'company_id': team.company_id.id,
            }
            for team in teams
        ]

    @http.route('/mail_plugin/ticket/create', type='json', auth='outlook', cors='*')
    def ticket_create(self, partner_id, email_body, email_subject=None, team_id=None):
        partner = request.env['res.partner'].browse(partner_id).exists()
        if not partner:
            return {'error': 'partner_not_found'}

        team = request.env['helpdesk.ticket.team'].browse(team_id).exists() if team_id else self._get_default_team()
        values = self._prepare_ticket_values(partner, email_subject, email_body, team=team)
        ticket = request.env['helpdesk.ticket'].with_company(values.get('company_id') or request.env.company.id).create(values)
        return {
            'ticket_id': ticket.id,
            'name': ticket.name,
            'number': ticket.number,
            'url': self._get_ticket_url(ticket),
        }

    @http.route('/mail_client_extension/ticket/get_by_partner_id', type='json', auth='outlook', cors='*')
    def ticket_get_by_partner_id(self, partner, limit=5, offset=0, **kwargs):
        partner_record = request.env['res.partner'].browse(partner).exists()
        if not partner_record:
            return {'tickets': []}
        commercial_partner = partner_record.commercial_partner_id or partner_record
        tickets = request.env['helpdesk.ticket'].search(
            ['|', ('partner_id', '=', partner_record.id), ('customer_id', '=', commercial_partner.id)],
            offset=offset,
            limit=limit,
            order='priority desc, id desc',
        )
        return {
            'tickets': [
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
        }

    @http.route('/mail_client_extension/ticket/open', type='http', auth='user')
    def helpdesk_ticket_open(self, ticket_id):
        action = request.env.ref('helpdesk_mail_plugin.helpdesk_ticket_action_form_edit')
        return request.redirect(f'/odoo/action-{action.id}/{int(ticket_id)}?edit=1')
