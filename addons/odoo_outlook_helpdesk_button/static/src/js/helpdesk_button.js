/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { OutlookPanel } from "@odoo_outlook/components/outlook_panel/outlook_panel";

patch(OutlookPanel.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },
    _getHelpdeskTicketPayload() {
        const mail = this.props?.mail || {};
        const sender = mail.from || mail.sender || mail.author || {};
        return {
            email_subject: mail.subject || mail.title || "Sin asunto",
            email_body: mail.body || mail.body_html || mail.htmlBody || mail.bodyHtml || mail.preview || "",
            sender_email:
                sender.email ||
                sender.address ||
                mail.from_email ||
                mail.email_from ||
                mail.senderEmail ||
                mail.authorEmail ||
                (typeof mail.from === "string" ? mail.from : ""),
            sender_name:
                sender.name ||
                mail.from_name ||
                mail.senderName ||
                mail.authorName ||
                "",
        };
    },
    _getHelpdeskTicketFallbackUrl(payload) {
        return `/web#model=helpdesk.ticket&view_type=form&default_name=${encodeURIComponent(payload.email_subject || "Sin asunto")}&default_description=${encodeURIComponent(payload.email_body || "")}&default_partner_name=${encodeURIComponent(payload.sender_name || "")}&default_partner_email=${encodeURIComponent(payload.sender_email || "")}`;
    },
    async createHelpdeskTicket() {
        const payload = this._getHelpdeskTicketPayload();
        try {
            const result = await rpc("/odoo_outlook_helpdesk_button/ticket/create", payload);
            if (result?.url) {
                window.open(result.url, "_blank", "noopener");
            }
            this.notification?.add(_t("Ticket creado correctamente desde Outlook."), {
                type: "success",
            });
        } catch (error) {
            console.error("No se pudo crear el ticket desde Outlook", error);
            this.notification?.add(
                _t("No se pudo crear el ticket automáticamente. Se abrirá el formulario precargado."),
                { type: "warning" }
            );
            window.open(this._getHelpdeskTicketFallbackUrl(payload), "_blank", "noopener");
        }
    },
});
