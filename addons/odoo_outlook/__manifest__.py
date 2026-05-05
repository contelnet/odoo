{
    "name": "Odoo Outlook Add-In",
    "summary": "An Odoo connector add-in for Microsoft Outlook.",
    "description": "El add-in permite descargar el instalador y marca mensajes creados desde Outlook.",
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
    "assets": {
        "web.assets_backend": [
            "odoo_outlook/static/src/js/thread.js",
            "odoo_outlook/static/src/css/outlook.css"
        ]
    },
    "qweb": [
        "views/templates.xml"
    ],
    "images": [
        "static/description/oregano.jpg"
    ],
    "installable": True,
    "application": True
}
