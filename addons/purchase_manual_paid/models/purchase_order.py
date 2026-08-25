import re
from odoo import models, fields, api

# ---------------------------------------------------------
# 1. CABECERA DEL PEDIDO
# ---------------------------------------------------------
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_manually_paid = fields.Boolean(
        string="¿Pagado?",
        help="Marca manualmente si ya has pagado este pedido.",
        default=False,
        tracking=True
    )

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    is_manually_paid = fields.Boolean(
        string="¿Pagado?",
        help="Marca manualmente si ya has pagado este pedido.",
        default=False,
        tracking=True
    )

    def action_force_save(self):
        """
        Este botón no necesita hacer nada especial en Python.
        El simple hecho de pulsarlo obliga a Odoo a guardar el documento,
        haciendo que salte nuestra lógica de creación/borrado de seriales.
        """
        return True

# ---------------------------------------------------------
# 2. LÍNEAS DEL PEDIDO (Creación y Borrado de Seriales)
# ---------------------------------------------------------
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    serial_numbers = fields.Text(
        string='Números de Serie',
        help='Pega aquí los números de serie de los productos.'
    )

    def _generar_lotes_automaticos(self):
        """Crea los números de serie que sean nuevos."""
        for line in self:
            if line.serial_numbers and line.product_id:
                seriales_sucios = re.split(r'[\n,;]+', line.serial_numbers)
                
                # 1. Crear en stock.lot oficial
                if 'stock.lot' in self.env:
                    StockLot = self.env['stock.lot']
                    for serial in seriales_sucios:
                        sn_limpio = serial.strip()
                        if sn_limpio:
                            existe = StockLot.search([
                                ('name', '=', sn_limpio),
                                ('product_id', '=', line.product_id.id)
                            ], limit=1)
                            
                            if not existe:
                                StockLot.create({
                                    'name': sn_limpio,
                                    'product_id': line.product_id.id,
                                    'company_id': line.company_id.id or self.env.company.id,
                                })
                                
                # 2. Inyectar en tu pestaña personalizada
                if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                    nuevos_custom = []
                    nombres_existentes = line.product_id.product_tmpl_id.serial_number_ids.mapped('name')
                    
                    for serial in seriales_sucios:
                        sn_limpio = serial.strip()
                        if sn_limpio and sn_limpio not in nombres_existentes:
                            nuevos_custom.append((0, 0, {'name': sn_limpio}))
                    
                    if nuevos_custom:
                        line.product_id.product_tmpl_id.write({
                            'serial_number_ids': nuevos_custom
                        })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._generar_lotes_automaticos()
        return lines

    def write(self, vals):
        # --- NUEVA MAGIA: Detectar si has borrado números de serie ---
        if 'serial_numbers' in vals:
            for line in self:
                old_text = line.serial_numbers or ""
                new_text = vals.get('serial_numbers') or ""

                # Sacamos los seriales que había antes y los que hay ahora
                old_serials = {s.strip() for s in re.split(r'[\n,;]+', old_text) if s.strip()}
                new_serials = {s.strip() for s in re.split(r'[\n,;]+', new_text) if s.strip()}

                # Restamos para ver cuáles han desaparecido del texto
                serials_to_delete = old_serials - new_serials

                if serials_to_delete and line.product_id:
                    # A. Borrar del registro oficial
                    if 'stock.lot' in self.env:
                        lots_to_delete = self.env['stock.lot'].search([
                            ('name', 'in', list(serials_to_delete)),
                            ('product_id', '=', line.product_id.id)
                        ])
                        if lots_to_delete:
                            try:
                                lots_to_delete.unlink()
                            except Exception:
                                # Si Odoo bloquea el borrado (ej. ya lo has vendido), lo ignoramos por seguridad.
                                pass

                    # B. Borrar de tu pestaña personalizada
                    if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                        custom_serials = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                            lambda s: s.name in serials_to_delete
                        )
                        if custom_serials:
                            # El código (2, ID, 0) es la orden interna de Odoo para borrar ese registro
                            line.product_id.product_tmpl_id.write({
                                'serial_number_ids': [(2, custom.id, 0) for custom in custom_serials]
                            })

        # --- Fin de la nueva magia ---

        res = super().write(vals)
        if 'serial_numbers' in vals:
            self._generar_lotes_automaticos()
        return res