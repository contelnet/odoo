from odoo import http
from odoo.http import request


class OutlookHelpdeskTicketController(http.Controller):
    @http.route(
        "/odoo_outlook_helpdesk_button/ticket/create",
        type="json",
        auth="user",
    )
    def create_helpdesk_ticket(self, email_subject=None, email_body=None, sender_email=None, sender_name=None):
        ticket = request.env["helpdesk.ticket"].create_from_outlook_payload(
            email_subject=email_subject,
            email_body=email_body,
            sender_email=sender_email,
            sender_name=sender_name,
        )
        base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        return {
            "ticket_id": ticket.id,
            "ticket_name": ticket.name,
            "url": f"{base_url}/web#id={ticket.id}&model=helpdesk.ticket&view_type=form",
        }
