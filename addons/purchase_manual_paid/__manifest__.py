{
    'name': 'Compras: Toggle de Pagado y Relacionados',
    'version': '18.0.1.0',
    'category': 'Purchases',
    'depends': ['purchase', 'product'],
    'data': [
        'views/purchase_order_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
}