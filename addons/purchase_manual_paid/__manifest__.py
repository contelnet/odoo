{
    'name': 'Compras: Toggle de Pagado y Relacionados',
    'version': '18.0.1.0',
    'category': 'Purchases',
    'depends': ['purchase', 'product', 'sale', 'stock'],
    'data': [
        'views/purchase_order_views.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}