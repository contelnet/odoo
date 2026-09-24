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

    helpdesk_invoice_date = fields.Date(string="Fecha de la factura")
    helpdesk_payment_reference = fields.Char(string="Referencia de pago")
    helpdesk_invoice_date_due = fields.Date(string="Fecha de vencimiento")

    # 🔥 CAMPO: Interruptor de confirmación automática 🔥
    is_express_order = fields.Boolean(
        string="Pedido Exprés", 
        default=False,
        help="Si está marcado, el pedido se confirmará automáticamente al guardar con líneas."
    )

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            lines = self.env['purchase.order.line'].search([('serial_numbers', operator, name)])
            order_ids = lines.mapped('order_id').ids
            
            search_domain = [
                '|', '|',
                ('name', operator, name),
                ('partner_ref', operator, name),
                ('id', 'in', order_ids)
            ]
            domain = search_domain + domain
            
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    @api.onchange('order_line')
    def _onchange_order_line_canons(self):
        if self.env.context.get('skip_canon_recalc'):
            return

        # 🔥 ESCUDO ANTI-REFRESCO: Si no hay necesidad matemática de hacer nada, huimos rápido.
        has_canon_needs = False
        has_automatic_canon = False
        
        for line in self.order_line:
            if line.product_id:
                if line.name and line.name.startswith("Canon aplicado"):
                    has_automatic_canon = True
                elif hasattr(line.product_id.product_tmpl_id, 'canon_amount') and line.product_id.product_tmpl_id.canon_amount > 0:
                    has_canon_needs = True

        if not has_canon_needs and not has_automatic_canon:
            return # Salimos sin tocar la BBDD para no borrar tu Canon manual.

        canon_product = self.env['product.product'].search([('default_code', '=', 'CANON')], limit=1)
        if not canon_product:
            return

        canon_needs = {}
        
        # 1. Agrupar cantidades y el importe del canon
        for line in self.order_line:
            if line.display_type or line.product_id.id == canon_product.id:
                continue
                
            canon_amount = line.product_id.product_tmpl_id.canon_amount
            if canon_amount > 0:
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

        # 2. Ajustar líneas de canon existentes
        lines_to_remove = self.env['purchase.order.line']
        for line in self.order_line:
            if line.product_id.id == canon_product.id:
                
                # BLINDAJE: Ignoramos el manual
                if not line.name or not line.name.startswith("Canon aplicado"):
                    continue

                price = 0.0
                if line.name:
                    match = re.search(r'\((\d+(?:\.\d+)?)€\)', line.name)
                    if match:
                        price = float(match.group(1))
                        
                if price == 0.0 and line.price_unit > 0:
                    price = line.price_unit

                if price in canon_needs and canon_needs[price]['qty'] > 0:
                    new_qty = canon_needs[price]['qty']
                    refs_str = ", ".join(sorted(canon_needs[price]['refs']))
                    new_name = f"Canon aplicado [{refs_str}] ({price}€)"
                    
                    # SEGURO: Solo tocamos la línea si los valores han cambiado realmente
                    if line.product_qty != new_qty:
                        line.product_qty = new_qty
                    if line.price_unit != price:
                        line.price_unit = price 
                    if line.name != new_name:
                        line.name = new_name
                    
                    canon_needs[price]['qty'] = 0
                else:
                    lines_to_remove += line
                    
        if lines_to_remove:
            self.order_line -= lines_to_remove

        # 3. Crear nuevas líneas forzando precio
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

    def _recalculate_canons(self):
        canon_product = self.env['product.product'].search([('default_code', '=', 'CANON')], limit=1)
        if not canon_product:
            return

        for order in self:
            canon_needs = {} 
            for line in order.order_line:
                if line.product_id.id == canon_product.id:
                    continue
                    
                canon_amount = line.product_id.product_tmpl_id.canon_amount
                if canon_amount > 0:
                    if canon_amount in canon_needs:
                        canon_needs[canon_amount] += line.product_qty 
                    else:
                        canon_needs[canon_amount] = line.product_qty
                        
            existing_canon_lines = order.order_line.filtered(lambda l: l.product_id.id == canon_product.id)
            for c_line in existing_canon_lines:
                
                # BLINDAJE: Ignoramos el manual al guardar
                if not c_line.name or not c_line.name.startswith("Canon aplicado"):
                    continue

                price = c_line.price_unit
                if price in canon_needs and canon_needs[price] > 0:
                    if c_line.product_qty != canon_needs[price]:
                        c_line.with_context(skip_canon_recalc=True).write({'product_qty': canon_needs[price]})
                    canon_needs[price] = 0
                else:
                    c_line.with_context(skip_canon_recalc=True).unlink()
                    
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
        return True

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.partner_id:
                for line in order.order_line:
                    if line.product_id and line.product_id.product_tmpl_id:
                        line.product_id.product_tmpl_id.supplier_partner_id = order.partner_id.id
        return res

    # 🔥 LÓGICA: Auto-confirmación del pedido exprés 🔥
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.is_express_order and order.state in ['draft', 'sent'] and order.order_line:
                order.button_confirm()
        return orders

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            if order.is_express_order and order.state in ['draft', 'sent'] and order.order_line:
                order.button_confirm()
        return res

    
# ---------------------------------------------------------
# 2. LÍNEAS DEL PEDIDO (Creación, Desglose Masivo y Borrado de Seriales)
# ---------------------------------------------------------
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # 🔥 MARTILLO 1: Sobreescribimos el método con el nombre KILOMÉTRICO de Odoo moderno 🔥
    @api.depends('product_qty', 'product_uom', 'company_id', 'product_id', 'partner_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        # 1. Dejamos que Odoo haga su trabajo por defecto
        try:
            super()._compute_price_unit_and_date_planned_and_name()
        except AttributeError:
            pass
            
        # 2. Machacamos el precio del Canon (Solo a los automáticos)
        for line in self:
            if line.product_id and line.product_id.default_code == 'CANON':
                if line.name and line.name.startswith("Canon aplicado"):
                    match = re.search(r'\((\d+(?:\.\d+)?)€\)', line.name)
                    if match:
                        new_price = float(match.group(1))
                        if line.price_unit != new_price:
                            line.price_unit = new_price

    # 🔥 MARTILLO 2: El Plan B infalible. Si la interfaz gráfica intenta ponerlo a cero, lo forzamos al instante 🔥
    @api.onchange('product_qty', 'product_id', 'name')
    def _onchange_force_canon_price_ui(self):
        for line in self:
            if line.product_id and line.product_id.default_code == 'CANON':
                if line.name and line.name.startswith("Canon aplicado"):
                    match = re.search(r'\((\d+(?:\.\d+)?)€\)', line.name)
                    if match:
                        new_price = float(match.group(1))
                        if line.price_unit != new_price:
                            line.price_unit = new_price

    serial_numbers = fields.Text(
        string='Números de Serie',
        help='Pega aquí los números de serie de los productos.'
    )
    
    def _generar_lotes_automaticos(self):
        for line in self:
            if line.serial_numbers and line.product_id:
                seriales_sucios = [s.strip() for s in re.split(r'[\s\t\n,;]+', line.serial_numbers) if s.strip()]
                
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
        
        # Refuerzo de guardado: Forzamos el precio otra vez al tocar la Base de Datos
        for line in lines:
            if line.product_id.default_code == 'CANON' and line.name and line.name.startswith("Canon aplicado"):
                match = re.search(r'\((\d+(?:\.\d+)?)€\)', line.name)
                if match:
                    new_price = float(match.group(1))
                    if line.price_unit != new_price:
                        line.price_unit = new_price

        lines._generar_lotes_automaticos()
        return lines

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        if self.serial_numbers and self.product_id:
            seriales_sucios = [s.strip() for s in re.split(r'[\s\t\n,;]+', self.serial_numbers) if s.strip()]
            if seriales_sucios:
                primer_serial = seriales_sucios[0]
                if hasattr(self.product_id.product_tmpl_id, 'serial_number_ids'):
                    serial_rec = self.product_id.product_tmpl_id.serial_number_ids.filtered(
                        lambda s: s.name == primer_serial
                    )
                    if serial_rec:
                        res['serial_number_id'] = serial_rec[0].id
        return res

    def write(self, vals):
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

    def unlink(self):
        for line in self:
            # 🔥 BLINDAJE CONTRA EL ERROR VIRTUAL_129
            # Si el ID no es un número entero en Base de Datos (es temporal o de la vista), saltamos:
            if not isinstance(line.id, int):
                continue
                
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