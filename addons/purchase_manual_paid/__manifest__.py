{
    'name': 'Compras: Toggle de Pagado y Relacionados',
    'version': '18.0.1.0',
    'category': 'Purchases',
    # 1. AÑADIMOS EL HELPDESK AQUÍ PARA QUE PYTHON LEA TU ARCHIVO
    'depends': ['purchase', 'product', 'sale', 'stock', 'helpdesk_mgmt'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_serial_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}