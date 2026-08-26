from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProductTemplateSerialNumber(models.Model):
    _name = "product.template.serial.number"
    _description = "Product Serial Number"
    _order = "id desc"

    # Se queda en False para que no obligue al crear el producto
    name = fields.Char(string="Numero de serie", required=False) 
    
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Producto",
        required=True,
        ondelete="cascade",
    )
    create_date = fields.Datetime(string="Fecha de alta", readonly=True)

    _sql_constraints = [
        (
            "product_template_serial_unique",
            "unique(product_tmpl_id, name)",
            "El numero de serie ya existe para este producto.",
        )
    ]

    # --- NUEVA MAGIA: Evitar guardados en blanco o con espacios ---
    @api.constrains('name')
    def _check_name_not_blank(self):
        for record in self:
            # Si el campo no existe o al quitarle los espacios se queda vacío...
            if not record.name or not record.name.strip():
                raise ValidationError("¡Atención! No puedes añadir una línea de número de serie en blanco.")