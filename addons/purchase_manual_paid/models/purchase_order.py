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

    # 👇 AÑADE ESTAS TRES LÍNEAS AQUÍ 👇
    helpdesk_invoice_date = fields.Date(string="Fecha de la factura")
    helpdesk_payment_reference = fields.Char(string="Referencia de pago")
    helpdesk_invoice_date_due = fields.Date(string="Fecha de vencimiento")
    # 👆 ---------------------------- 👆

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

    def _compute_price_unit(self):
        # 1. Dejamos que Odoo haga su trabajo y ponga el precio estándar (o sea, 0€)
        super()._compute_price_unit()
        
        # 2. Entramos a saco a machacar ese precio antes de que llegue a la pantalla
        for line in self:
            if line.product_id and line.product_id.default_code == 'CANON':
                if line.name:
                    # Buscamos el precio entre paréntesis en la etiqueta que generamos
                    match = re.search(r'\(([\d\.]+)€\)', line.name)
                    if match:
                        # ¡ZAS! Fijamos el precio a la fuerza
                        line.price_unit = float(match.group(1))

    @api.onchange('order_line')
    def _onchange_order_line_canons(self):
        # Buscamos nuestro producto comodín
        canon_product = self.env['product.product'].search([('default_code', '=', 'CANON')], limit=1)
        if not canon_product:
            return

        # Ahora guardaremos la cantidad Y una lista (set) de referencias
        canon_needs = {}
        
        # 1. Sumar cantidades y recolectar Referencias (Part Numbers)
        for line in self.order_line:
            if line.display_type or line.product_id.id == canon_product.id:
                continue
                
            canon_amount = line.product_id.product_tmpl_id.canon_amount
            if canon_amount > 0:
                # Cogemos el Part Number (default_code). Si no tiene, usamos el nombre.
                ref = line.product_id.default_code or line.product_id.name
                
                if canon_amount in canon_needs:
                    canon_needs[canon_amount]['qty'] += line.product_qty
                    if ref:
                        canon_needs[canon_amount]['refs'].add(ref)
                else:
                    canon_needs[canon_amount] = {
                        'qty': line.product_qty,
                        'refs': {ref} if ref else set()
                    }

        # 2. Ajustar las líneas existentes
        lines_to_remove = self.env['purchase.order.line']
        for line in self.order_line:
            if line.product_id.id == canon_product.id:
                price = 0.0
                if line.name:
                    match = re.search(r'\(([\d\.]+)€\)', line.name)
                    if match:
                        price = float(match.group(1))
                        
                if price == 0.0 and line.price_unit > 0:
                    price = line.price_unit

                if price in canon_needs and canon_needs[price]['qty'] > 0:
                    line.product_qty = canon_needs[price]['qty']
                    line.price_unit = price
                    
                    # Actualizamos el nombre en vivo por si han añadido productos nuevos
                    refs_str = ", ".join(sorted(canon_needs[price]['refs']))
                    line.name = f"Canon aplicado [{refs_str}] ({price}€)"
                    
                    canon_needs[price]['qty'] = 0
                else:
                    lines_to_remove += line
                    
        if lines_to_remove:
            self.order_line -= lines_to_remove

        # 3. Crear las que falten
        new_lines = []
        for price, data in canon_needs.items():
            if data['qty'] > 0:
                refs_str = ", ".join(sorted(data['refs']))
                new_lines.append((0, 0, {
                    'product_id': canon_product.id,
                    'name': f"Canon aplicado [{refs_str}] ({price}€)",
                    'product_qty': data['qty'],
                    'price_unit': price,
                }))
                
        if new_lines:
            self.update({'order_line': new_lines})
            
        # 4. EL MARTILLAZO FINAL 🔨 (Para salvar el precio de las garras de Odoo)
        for line in self.order_line:
            if line.product_id.id == canon_product.id and line.name:
                match = re.search(r'\(([\d\.]+)€\)', line.name)
                if match:
                    line.price_unit = float(match.group(1))


        
    def _recalculate_canons(self):
        # Buscamos nuestro producto comodín por su Referencia Interna
        canon_product = self.env['product.product'].search([('default_code', '=', 'CANON')], limit=1)
        if not canon_product:
            return

        for order in self:
            canon_needs = {} # Guardará {precio_del_canon: cantidad_necesaria}
            
            # 1. Agrupar todas las líneas normales y sumar los cánones que exigen
            for line in order.order_line:
                # Ignoramos si la línea es el propio producto Canon para no hacer un bucle infinito
                if line.product_id.id == canon_product.id:
                    continue
                    
                canon_amount = line.product_id.product_tmpl_id.canon_amount
                if canon_amount > 0:
                    if canon_amount in canon_needs:
                        canon_needs[canon_amount] += line.product_qty #
                    else:
                        canon_needs[canon_amount] = line.product_qty
                        
            # 2. Localizar qué líneas de Canon YA existen en este pedido
            existing_canon_lines = order.order_line.filtered(lambda l: l.product_id.id == canon_product.id)
            
            # 3. Ajustar cantidades de los existentes o borrarlos si ya no hacen falta
            for c_line in existing_canon_lines:
                price = c_line.price_unit
                if price in canon_needs and canon_needs[price] > 0:
                    # Si existe y la cantidad es distinta, la actualizamos
                    if c_line.product_qty != canon_needs[price]:
                        c_line.with_context(skip_canon_recalc=True).write({'product_qty': canon_needs[price]})
                    # Lo tachamos de la lista de necesidades
                    canon_needs[price] = 0
                else:
                    # Si existe pero ya no lo necesitamos (ej. borraron el monitor), autodestruimos la línea de canon
                    c_line.with_context(skip_canon_recalc=True).unlink()
                    
            # 4. Crear de cero las líneas de Canon que falten
            lines_to_create = []
            for price, qty in canon_needs.items():
                if qty > 0:
                    lines_to_create.append((0, 0, {
                        'product_id': canon_product.id,
                        'name': f"Canon aplicado ({price}€)",
                        'product_qty': qty,
                        'price_unit': price,
                    }))
            
            if lines_to_create:
                order.with_context(skip_canon_recalc=True).write({'order_line': lines_to_create})

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
        # --- DESGLOSE MASIVO AL CREAR LÍNEAS ---
        expanded_vals_list = []
        for vals in vals_list:
            serial_text = vals.get('serial_numbers', '')
            if serial_text:
                seriales = [s.strip() for s in re.split(r'[\s\t\n,;]+', serial_text) if s.strip()]
                if len(seriales) > 1:
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

                if not new_text.strip():
                    if old_text.strip() and line.product_id:
                        serial_a_borrar = old_text.strip()
                        if 'stock.lot' in self.env:
                            lot = self.env['stock.lot'].search([
                                ('name', '=', serial_a_borrar),
                                ('product_id', '=', line.product_id.id)
                            ], limit=1)
                            if lot:
                                try: lot.unlink()
                                except: pass
                        if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                            custom_lot = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                                lambda s: s.name == serial_a_borrar
                            )
                            if custom_lot:
                                line.product_id.product_tmpl_id.write({
                                    'serial_number_ids': [(2, custom_lot.id, 0)]
                                })
                    
                    line.unlink()
                    continue

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
        for line in self:
            if line.serial_numbers and line.product_id:
                seriales_a_borrar = [s.strip() for s in re.split(r'[\s\t\n,;]+', line.serial_numbers) if s.strip()]
                
                if seriales_a_borrar:
                    if hasattr(line.product_id.product_tmpl_id, 'serial_number_ids'):
                        custom_serials = line.product_id.product_tmpl_id.serial_number_ids.filtered(
                            lambda s: s.name in seriales_a_borrar
                        )
                        if custom_serials:
                            custom_serials.unlink()
                            continue
                            
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

        return super().unlink()