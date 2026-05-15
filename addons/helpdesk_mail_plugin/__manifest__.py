# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Mail Plugin',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'sequence': 5,
    'summary': 'Integrate Outlook and Gmail with Helpdesk tickets.',
    'description': 'Turn emails received in your mailbox into helpdesk tickets and log their content as internal notes.',
    'website': 'https://www.odoo.com',
    'depends': [
        'helpdesk_mgmt',
        'mail_plugin',
    ],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
