{
    "name": "Outlook Helpdesk Add-In",
    "summary": "Descarga y prepara el complemento de Outlook para crear tickets en Odoo.",
    "description": "Pantalla de preparación del complemento de Outlook para un uso profesional con tickets de helpdesk en Odoo.",
    "author": "Atteli - Juliusz Sosinowicz",
    "website": "http://atteli.com",
    "category": "Productivity",
    "version": "18.0.1.0.0",
    "license": "GPL-3",
    "depends": ["base", "crm", "project", "mail", "web"],
    "data": [
        "views/outlook.xml",
        "records/ir.model.access.csv"
    ],
    "images": [
        "static/description/oregano.jpg"
    ],
    "installable": True,
    "application": True
}
