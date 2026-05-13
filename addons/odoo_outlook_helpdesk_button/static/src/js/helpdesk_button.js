/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OutlookPanel } from "@odoo_outlook/components/outlook_panel/outlook_panel";

patch(OutlookPanel.prototype, {
    setup() {
        super.setup();
    },
    createHelpdeskTicket() {
        const subject = this.props?.mail?.subject || "Sin asunto";
        const body = this.props?.mail?.body || "";
        const url = `/web#model=helpdesk.ticket&view_type=form&default_name=${encodeURIComponent(subject)}&default_description=${encodeURIComponent(body)}`;
        window.open(url, "_blank");
    },
});
