import re

from odoo import _, api, models, tools
from odoo.tools import html2plaintext, plaintext2html


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    @api.model
    def create_from_outlook_payload(self, email_subject=None, email_body=None, sender_email=None, sender_name=None):
        self.check_access_rights("create")

        parsed_name, parsed_email = tools.parse_contact_from_email(sender_email or "")
        normalized_email = tools.email_normalize(parsed_email or sender_email or "")
        display_name = (sender_name or parsed_name or "").strip()

        partner = self.env["res.partner"]
        if normalized_email:
            partner = self.env["res.partner"].search(
                [
                    "|",
                    ("email_normalized", "=", normalized_email),
                    ("email", "=ilike", normalized_email),
                ],
                limit=1,
            )

        commercial_partner = partner.commercial_partner_id if partner else self.env["res.partner"]
        company = partner.company_id or commercial_partner.company_id or self.env.company
        team = self.env.user.helpdesk_team_ids.sorted(lambda team_rec: (team_rec.sequence, team_rec.id))[:1]
        channel = self.env.ref("helpdesk_mgmt.helpdesk_ticket_channel_email", raise_if_not_found=False)

        subject = re.sub(r"[*_`]+", "", html2plaintext(email_subject or "")).strip() or _("Caso creado desde Outlook")
        body = (email_body or "").strip()
        if body and "<" not in body:
            body = plaintext2html(body)
        body = body or plaintext2html(_("Correo recibido desde Outlook sin contenido visible."))

        partner_email = partner.email or normalized_email or False
        partner_label = display_name or partner.name or normalized_email or _("Contacto Outlook")

        values = {
            "name": subject,
            "description": body,
            "company_id": company.id,
            "channel_id": channel.id if channel else False,
            "partner_name": partner_label,
            "partner_email": partner_email,
            "caller_name": partner_label,
        }
        if team:
            values["team_id"] = team.id
        if partner:
            if partner.is_company:
                values["customer_id"] = commercial_partner.id
            else:
                values.update({
                    "partner_id": partner.id,
                    "customer_id": commercial_partner.id if commercial_partner else False,
                })

        ticket = self.with_company(company).create(values)
        ticket.message_post(
            body=plaintext2html(
                _("Caso creado automáticamente desde Outlook.")
            ),
            subtype_xmlid="mail.mt_note",
        )
        return ticket
