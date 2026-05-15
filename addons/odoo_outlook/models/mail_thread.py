# -*- coding: utf-8 -*-

from xmlrpc.client import Binary

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, *args, **kwargs):
        if args:
            legacy_keys = (
                'body',
                'subject',
                'message_type',
                'subtype',
                'parent_id',
                'attachments',
                'content_subtype',
            )
            legacy_values = dict(zip(legacy_keys, args))

            if 'body' not in kwargs and legacy_values.get('body') is not None:
                kwargs['body'] = legacy_values['body']
            if 'subject' not in kwargs and legacy_values.get('subject'):
                kwargs['subject'] = legacy_values['subject']
            if 'message_type' not in kwargs and legacy_values.get('message_type'):
                kwargs['message_type'] = legacy_values['message_type']
            if 'parent_id' not in kwargs and legacy_values.get('parent_id'):
                kwargs['parent_id'] = legacy_values['parent_id']
            if 'attachments' not in kwargs and legacy_values.get('attachments'):
                kwargs['attachments'] = legacy_values['attachments']

            subtype = legacy_values.get('subtype')
            if subtype and 'subtype_id' not in kwargs and 'subtype_xmlid' not in kwargs:
                if isinstance(subtype, int):
                    kwargs['subtype_id'] = subtype
                elif isinstance(subtype, str):
                    kwargs['subtype_xmlid'] = subtype if '.' in subtype else f'mail.{subtype}'

            if 'body_is_html' not in kwargs and legacy_values.get('content_subtype') == 'html':
                kwargs['body_is_html'] = True

        return super().message_post(**kwargs)

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