{
    'name': 'Compras: Toggle de Pagado y Relacionados',
    'version': '18.0.1.0',
    'category': 'Purchases',
    'depends': ['purchase', 'product', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_serial_wizard_views.xml'
    ],
    'installable': True,
    'application': False,
}