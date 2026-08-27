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

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permite buscar pedidos de compra escribiendo directamente el número de serie en la barra de búsqueda.
        """
        domain = domain or []
        if name:
            # Buscamos qué líneas de compra tienen este número de serie
            lines = self.env['purchase.order.line'].search([('serial_numbers', operator, name)])
            order_ids = lines.mapped('order_id').ids
            
            # Ampliamos el dominio para que busque por el nombre del pedido (P0000x), referencia o si el ID está en los pedidos encontrados
            search_domain = [
                '|', '|',
                ('name', operator, name),
                ('partner_ref', operator, name),
                ('id', 'in', order_ids)
            ]
            domain = search_domain + domain
            
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def action_force_save(self):
        """
        Este botón no necesita hacer nada especial en Python.
        El simple hecho de pulsarlo obliga a Odoo a guardar el documento,
        haciendo que salte nuestra lógica de creación/borrado de seriales.
        """
        return True

    # --- NUEVA MAGIA: Guardar proveedor en la ficha del producto ---
    def button_confirm(self):
        # 1. Ejecutamos el comportamiento estándar de Odoo para confirmar el pedido
        res = super(PurchaseOrder, self).button_confirm()
        
        # 2. Recorremos los productos del pedido y les actualizamos el proveedor
        for order in self:
            if order.partner_id:
                for line in order.order_line:
                    # Nos aseguramos de que haya un producto en la línea
                    if line.product_id and line.product_id.product_tmpl_id:
                        # Asignamos el proveedor al campo personalizado
                        line.product_id.product_tmpl_id.supplier_partner_id = order.partner_id.id
                        
        return res

# ---------------------------------------------------------
# 2. LÍNEAS DEL PEDIDO (Creación, Desglose Masivo y Borrado de Seriales)
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
                seriales_sucios = [s.strip() for s in re.split(r'[\s\t\n,;]+', line.serial_numbers) if s.strip()]
                
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
        # Desglose masivo al crear líneas si se pegan varios seriales
        expanded_vals_list = []
        for vals in vals_list:
            serial_text = vals.get('serial_numbers', '')
            if serial_text:
                seriales = [s.strip() for s in re.split(r'[\s\t\n,;]+', serial_text) if s.strip()]
                if len(seriales) > 1:
                    # Clonamos la línea dividiendo los seriales uno a uno y cantidad a 1.0
                    for serial in seriales:
                        new_vals = vals.copy()
                        new_vals['serial_numbers'] = serial
                        new_vals['product_qty'] = 1.0
                        expanded_vals_list.append(new_vals)
                    continue
            expanded_vals_list.append(vals)

        lines = super().create(expanded_vals_list)
        lines._generar_lotes_automaticos()
        return lines

    def _prepare_account_move_line(self, move=False):
        # 1. Dejamos que Odoo prepare la línea de la factura de forma estándar
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        
        # 2. Si tenemos números de serie escritos en el pedido de compra...
        if self.serial_numbers and self.product_id:
            seriales_sucios = [s.strip() for s in re.split(r'[\s\t\n,;]+', self.serial_numbers) if s.strip()]
            if seriales_sucios:
                primer_serial = seriales_sucios[0]
                
                # Buscamos si existe ese número de serie en la pestaña personalizada del producto
                if hasattr(self.product_id.product_tmpl_id, 'serial_number_ids'):
                    serial_rec = self.product_id.product_tmpl_id.serial_number_ids.filtered(
                        lambda s: s.name == primer_serial
                    )
                    if serial_rec:
                        # Inyectamos el ID exacto que pide el campo many2one de la factura
                        res['serial_number_id'] = serial_rec[0].id
                        
        return res

    def write(self, vals):
        # --- DESGLOSE MASIVO EN EDICIÓN ---
        if 'serial_numbers' in vals and len(self) == 1:
            serial_text = vals.get('serial_numbers', '')
            if serial_text:
                seriales = [s.strip() for s in re.split(r'[\s\t\n,;]+', serial_text) if s.strip()]
                if len(seriales) > 1:
                    vals['serial_numbers'] = seriales[0]
                    vals['product_qty'] = 1.0
                    
                    order = self.order_id
                    for serial in seriales[1:]:
                        self.copy({
                            'order_id': order.id,
                            'serial_numbers': serial,
                            'product_qty': 1.0,
                        })

        # --- GESTIÓN DE BORRADO DE SERIALES Y LÍNEAS VACÍAS ---
        if 'serial_numbers' in vals:
            for line in self:
                old_text = line.serial_numbers or ""
                new_text = vals.get('serial_numbers') or ""

                # Si vacían el campo de golpe, borramos el serial asociado en la ficha del producto y la línea
                if not new_text.strip():
                    if old_text.strip() and line.product_id:
                        serial_a_borrar = old_text.strip()
                        # A. Borrar de stock.lot
                        if 'stock.lot' in self.env:
                            lot = self.env['stock.lot'].search([
                                ('name', '=', serial_a_borrar),
                                ('product_id', '=', line.product_id.id)
                            ], limit=1)
                            if lot:
                                try: lot.unlink()
                                except: pass
                        # B. Borrar de la pestaña personalizada del producto
                        if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                            custom_lot = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                                lambda s: s.name == serial_a_borrar
                            )
                            if custom_lot:
                                line.product_id.product_tmpl_id.write({
                                    'serial_number_ids': [(2, custom_lot.id, 0)]
                                })
                    
                    # Autodestruimos la línea vacía del pedido
                    line.unlink()
                    continue

                # Lógica estándar para listas si quedan restos
                old_serials = {s.strip() for s in re.split(r'[\s\t\n,;]+', old_text) if s.strip()}
                new_serials = {s.strip() for s in re.split(r'[\s\t\n,;]+', new_text) if s.strip()}
                serials_to_delete = old_serials - new_serials

                if serials_to_delete and line.product_id:
                    if 'stock.lot' in self.env:
                        lots_to_delete = self.env['stock.lot'].search([
                            ('name', 'in', list(serials_to_delete)),
                            ('product_id', '=', line.product_id.id)
                        ])
                        if lots_to_delete:
                            try: lots_to_delete.unlink()
                            except: pass

                    if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                        custom_serials = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                            lambda s: s.name in serials_to_delete
                        )
                        if custom_serials:
                            line.product_id.product_tmpl_id.write({
                                'serial_number_ids': [(2, custom.id, 0) for custom in custom_serials]
                            })

        if not self.exists():
            return True

        res = super().write(vals)
        if 'serial_numbers' in vals and self.exists():
            self._generar_lotes_automaticos()
        return res

    # --- NUEVA MAGIA: Limpiar el inventario al borrar la línea entera ---
# --- NUEVA MAGIA: Limpiar el inventario al borrar la línea entera ---
    def unlink(self):
        # Antes de que Odoo desintegre las líneas del pedido, rescatamos sus seriales
        for line in self:
            if line.serial_numbers and line.product_id:
                # Extraemos los seriales que estaban escritos en esta línea
                seriales_a_borrar = [s.strip() for s in re.split(r'[\s\t\n,;]+', line.serial_numbers) if s.strip()]
                
                if seriales_a_borrar:
                    # 1. Disparamos directamente el borrado de tu pestaña personalizada
                    if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                        custom_serials = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                            lambda s: s.name in seriales_a_borrar
                        )
                        if custom_serials:
                            # Al hacer unlink() aquí, Odoo ejecuta el chivato del chat 
                            # y borra el stock.lot automáticamente (lo que programamos antes)
                            custom_serials.unlink()
                            continue # Si ya lo hemos destruido, pasamos a la siguiente línea
                            
                    # 2. Fallback de seguridad: Si no hay pestaña, borramos de stock.lot a la fuerza
                    if 'stock.lot' in self.env:
                        lots_to_delete = self.env['stock.lot'].search([
                            ('name', 'in', seriales_a_borrar),
                            ('product_id', '=', line.product_id.id)
                        ])
                        if lots_to_delete:
                            try:
                                lots_to_delete.unlink()
                            except Exception:
                                pass

        # Una vez que hemos limpiado el rastro, dejamos que Odoo borre la línea del pedido
        return super().unlink()