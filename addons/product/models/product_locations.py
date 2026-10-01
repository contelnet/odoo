from odoo import fields, models

class ProductCatalogLocation(models.Model):
    _name = "product.catalog.location"
    _description = "Ubicaciones físicas del catálogo"
    _order = "name"

    name = fields.Char(string="Ubicación", required=True, help="Ej: Cajón 3, Pasillo A, Vitrina...")
    active = fields.Boolean(default=True)
    # Comentamos esto temporalmente:
    # product_ids = fields.One2many(...)