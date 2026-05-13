# -*- coding: utf-8 -*-

from xmlrpc.client import Binary

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _process_attachments_for_post(self, attachments, attachment_ids, message_values):
        normalized_attachments = []
        for attachment in attachments or []:
            if not isinstance(attachment, (list, tuple)):
                normalized_attachments.append(attachment)
                continue

            attachment_values = list(attachment)
            if len(attachment_values) >= 2 and isinstance(attachment_values[1], Binary):
                attachment_values[1] = attachment_values[1].data
            normalized_attachments.append(tuple(attachment_values))

        return super()._process_attachments_for_post(
            normalized_attachments, attachment_ids, message_values
        )