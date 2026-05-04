{
    "name": "Outlook Helpdesk Button",
    "version": "18.0.1.0.0",
    "depends": ["odoo_outlook"],
    "assets": {
        "odoo_outlook.assets": [
            "odoo_outlook_helpdesk_button/static/src/js/helpdesk_button.js",
            "odoo_outlook_helpdesk_button/static/src/xml/helpdesk_button.xml",
        ],
    },
    "author": "Contelnet / Pablo",
    "category": "Productivity",
    "summary": "Botón para crear tickets de helpdesk desde Outlook panel.",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}