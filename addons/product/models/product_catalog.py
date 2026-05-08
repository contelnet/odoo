from markupsafe import escape
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class Product(models.Model):
    _inherit = "product.template"

    def _setup_complete(self):
        res = super()._setup_complete()
        # Forzar desde módulo product que no se valide compañía en este campo
        # cuando lo añade el módulo helpdesk_product.
        helpdesk_location_field = self._fields.get("helpdesk_location_id")
        if helpdesk_location_field:
            helpdesk_location_field.check_company = False
        return res

    @api.model
    def _get_missing_comodel_fields(self, field_names=None):
        """Devuelve campos relacionales cuyo comodel no existe en el registro.

        Evita errores tipo:
        AttributeError: '_unknown' object has no attribute 'id'
        """
        candidate_names = field_names or list(self._fields.keys())
        missing = set()
        for name in candidate_names:
            field = self._fields.get(name)
            if not field or field.type not in ("many2one", "one2many", "many2many"):
                continue
            comodel = getattr(field, "comodel_name", False)
            if comodel and not self._is_model_available(comodel):
                missing.add(name)
        return missing

    def read(self, fields=None, load="_classic_read"):
        missing_fields = self._get_missing_comodel_fields(fields)
        if not missing_fields:
            return super().read(fields=fields, load=load)

        safe_fields = [f for f in (fields or list(self._fields.keys())) if f not in missing_fields]
        values_list = super().read(fields=safe_fields, load=load)
        for vals in values_list:
            for field_name in missing_fields:
                field = self._fields[field_name]
                vals[field_name] = False if field.type == "many2one" else []
        return values_list

    @api.model
    def _default_21_tax(self, tax_use):
        if not self._is_model_available("account.tax"):
            return False
        Tax = self.env["account.tax"]
        company_domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.env.company.id),
        ]

        # Coincidencia exacta solicitada: "21 % V" / "21 % C".
        exact_name = "21 % V" if tax_use == "sale" else "21 % C"
        exact_tax = Tax.search(
            [
                ("type_tax_use", "=", tax_use),
                ("amount_type", "=", "percent"),
                ("amount", "=", 21.0),
                ("name", "=", exact_name),
                *company_domain,
            ],
            order="company_id desc, sequence, id",
            limit=1,
        )
        if exact_tax:
            return exact_tax

        # Prioridad por nombre lógico: 21%V / 21%C (ignorando espacios y mayúsculas).
        tax_name = "21%V" if tax_use == "sale" else "21%C"
        candidates = Tax.search(
            [
                ("type_tax_use", "=", tax_use),
                ("amount_type", "=", "percent"),
                *company_domain,
            ],
            order="company_id desc, sequence, id",
        )
        for candidate in candidates:
            normalized = (candidate.name or "").upper().replace(" ", "")
            if normalized == tax_name:
                return candidate

        for candidate in candidates:
            if abs((candidate.amount or 0.0) - 21.0) < 1e-6:
                return candidate

        return False

    @api.model
    def _default_sale_taxes(self):
        return self._default_21_tax("sale")

    @api.model
    def _default_purchase_taxes(self):
        return self._default_21_tax("purchase")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Impuestos se asignan vía default=lambda en los campos y en create()
        # No manipular aquí para evitar conflictos con registros _unknown
        return res

    taxes_id = fields.Many2many(
        'account.tax',
        'product_taxes_rel',
        'prod_id',
        'tax_id',
        string="Impuestos de venta",
        help="Impuestos por defecto al vender el producto",
        default=lambda self: self._default_sale_taxes(),
    )
    supplier_taxes_id = fields.Many2many(
        'account.tax',
        'product_supplier_taxes_rel',
        'prod_id',
        'tax_id',
        string="Impuestos de compra",
        help="Impuestos por defecto al comprar el producto",
        default=lambda self: self._default_purchase_taxes(),
    )

    @api.model
    def _is_model_available(self, model_name):
        try:
            model = self.env.get(model_name)
        except Exception:
            return False
        return bool(model and getattr(model, "_name", None) == model_name)

    def init(self):
        """

        Evita errores `UndefinedColumn` al cargar `product.template`/`product.product`
        cuando existen campos nuevos en código pero aún no en la tabla SQL.
        """
        self.env.cr.execute(
            """
            ALTER TABLE product_template
                ADD COLUMN IF NOT EXISTS ticket_active boolean,
                ADD COLUMN IF NOT EXISTS product_mode varchar,
                ADD COLUMN IF NOT EXISTS product_business_type varchar,
                ADD COLUMN IF NOT EXISTS product_notes text,
                ADD COLUMN IF NOT EXISTS canon_amount numeric,
                ADD COLUMN IF NOT EXISTS has_imei boolean,
                ADD COLUMN IF NOT EXISTS imei_number varchar,
                ADD COLUMN IF NOT EXISTS purchase_tax_percent numeric,
                ADD COLUMN IF NOT EXISTS sale_tax_percent numeric,
                ADD COLUMN IF NOT EXISTS piece_input varchar,
                ADD COLUMN IF NOT EXISTS piece_product_id integer,
                ADD COLUMN IF NOT EXISTS serial_number_input varchar,
                ADD COLUMN IF NOT EXISTS supplier_partner_id integer,
                ADD COLUMN IF NOT EXISTS supplier_reference text,
                ADD COLUMN IF NOT EXISTS stock_location_id integer,
                ADD COLUMN IF NOT EXISTS stock_initial_qty numeric,
                ADD COLUMN IF NOT EXISTS stock_initial_applied_qty numeric,
                ADD COLUMN IF NOT EXISTS stock_initial_locked boolean,
                ADD COLUMN IF NOT EXISTS stock_last_synced_at timestamp
            """
        )

        self.env.cr.execute(
            """
            UPDATE product_template
               SET ticket_active = TRUE
             WHERE ticket_active IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET product_mode = 'pieces'
             WHERE product_mode IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET product_business_type = CASE
                    WHEN type = 'service' THEN 'service'
                    ELSE 'goods'
               END
             WHERE product_business_type IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET has_imei = FALSE
                    WHERE has_imei IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET stock_initial_qty = 0
             WHERE stock_initial_qty IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET stock_initial_applied_qty = 0
             WHERE stock_initial_applied_qty IS NULL
            """
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET stock_initial_locked = FALSE
             WHERE stock_initial_locked IS NULL
            """ 
        )
        self.env.cr.execute(
            """
            UPDATE product_template
               SET stock_initial_locked = TRUE
             WHERE COALESCE(stock_initial_applied_qty, 0) != 0
               AND stock_initial_locked = FALSE
            """
        )

    ticket_active = fields.Boolean(
        "Disponible para tickets", default=True, required=True
    )
    product_mode = fields.Selection(
        selection=[("single", "Producto unico"), ("pieces", "Por piezas")],
        string="Tipo de producto",
        default="single",
        required=True,
    )
    list_price = fields.Float(default=0.0)
    standard_price = fields.Float(default=0.0)
    product_business_type = fields.Selection(
        selection=[
            ("goods", "Bienes"),
            ("service", "Servicio"),
            ("software", "Software"),
        ],
        string="Tipo comercial",
        default="goods",
        required=True,
    )
    product_notes = fields.Text(string="Descripcion")
    canon_amount = fields.Monetary(
        string="Canon",
        currency_field="currency_id",
        help="Importe manual del canon aplicado al producto.",
    )
    has_imei = fields.Boolean(
        string="Tiene IMEI",
        help="Marcar cuando el producto tiene identificador IMEI.",
    )
    imei_number = fields.Char(
        string="IMEI",
        help="IMEI del dispositivo (normalmente 15 dígitos).",
    )
    has_serial_number = fields.Boolean(
        string="Tiene numero de serie",
        compute="_compute_has_serial_number",
        inverse="_inverse_has_serial_number",
    )
    piece_input = fields.Char(string="Anadir pieza")
    piece_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Añadir producto existente",
        help="Busca un producto existente y guárdalo para añadirlo como pieza.",
    )
    piece_ids = fields.One2many(
        comodel_name="product.template.piece",
        inverse_name="product_tmpl_id",
        string="Piezas",
    )
    piece_total_price = fields.Monetary(
        string="Total piezas",
        currency_field="cost_currency_id",
        compute="_compute_piece_total_price",
    )
    serial_number_input = fields.Char(
        string="Numero de serie",
    )
    serial_number_ids = fields.One2many(
        comodel_name="product.template.serial.number",
        inverse_name="product_tmpl_id",
        string="Numeros de serie",
    )
    serial_number_count = fields.Integer(
        string="N. series",
        compute="_compute_serial_number_count",
    )
    supplier_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Proveedor",
        domain=[("is_company", "=", True)],
    )
    supplier_reference = fields.Text(
        string="Referencia externa proveedor",
    )
    stock_qty = fields.Float(
        string="Stock",
        compute="_compute_stock_qty",
        digits="Product Unit of Measure",
        readonly=True,
        help="Stock disponible calculado por movimientos de inventario (compras/entradas/salidas).",
    )
    stock_real_qty = fields.Float(
        string="Stock real total",
        compute="_compute_stock_real_qty",
        digits="Product Unit of Measure",
        readonly=True,
        help="Stock total disponible en todas las ubicaciones internas de inventario.",
    )
    stock_in_today_qty = fields.Float(
        string="Entradas hoy",
        compute="_compute_stock_activity_summary",
        digits="Product Unit of Measure",
        readonly=True,
    )
    stock_out_today_qty = fields.Float(
        string="Salidas hoy",
        compute="_compute_stock_activity_summary",
        digits="Product Unit of Measure",
        readonly=True,
    )
    stock_last_move_at = fields.Datetime(
        string="Último movimiento",
        compute="_compute_stock_activity_summary",
        readonly=True,
    )
    
    service_sales_count = fields.Float(
        string="Contador de Ventas",
        compute="_compute_service_sales_count",
        readonly=True,
        help="Número total de unidades vendidas (solo para Servicios y Software)",
    )
    stock_last_move_ref = fields.Char(
        string="Referencia último movimiento",
        compute="_compute_stock_activity_summary",
        readonly=True,
    )
    stock_activity_period = fields.Selection(
        selection=[
            ("today", "Hoy"),
            ("7d", "Últimos 7 días"),
            ("30d", "Últimos 30 días"),
        ],
        string="Periodo",
        default="today",
        help="Periodo de análisis para entradas/salidas mostradas en el panel de inventario.",
    )
    stock_initial_qty = fields.Float(
        string="Stock inicial",
        default=0.0,
        digits="Product Unit of Measure",
        inverse="_inverse_stock_initial_qty",
        help="Cantidad inicial manual. Al guardar se suma/resta sobre el stock real.",
    )
    stock_initial_applied_qty = fields.Float(
        string="Stock inicial aplicado",
        default=0.0,
        digits="Product Unit of Measure",
        copy=False,
        readonly=True,
    )
    stock_initial_locked = fields.Boolean(
        string="Stock inicial bloqueado",
        default=False,
        copy=False,
        readonly=True,
    )
    stock_sync_status = fields.Selection(
        selection=[
            ("synced", "Sincronizado"),
            ("pending", "Pendiente de guardar"),
            ("unavailable", "No disponible"),
        ],
        string="Estado de sincronización",
        compute="_compute_stock_sync_status",
    )
    stock_last_synced_at = fields.Datetime(
        string="Última sincronización",
        readonly=True,
        copy=False,
    )
    stock_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Ubicacion",
        domain="[]",
        default=lambda self: self._default_stock_location_id(),
        check_company=False,
    )
    purchase_tax_amount = fields.Monetary(
        string="Impuesto de compra",
        currency_field="cost_currency_id",
        compute="_compute_tax_amounts",
    )
    purchase_tax_percent = fields.Float(
        string="% impuesto compra",
        compute="_compute_tax_percentages",
        digits=(16, 2),
    )
    purchase_total = fields.Monetary(
        string="Costo con impuesto",
        currency_field="cost_currency_id",
        compute="_compute_tax_amounts",
    )
    purchase_total_with_canon = fields.Monetary(
        string="Costo + canon",
        currency_field="cost_currency_id",
        compute="_compute_totals_with_canon",
    )
    sale_tax_amount = fields.Monetary(
        string="Impuesto de venta",
        currency_field="currency_id",
        compute="_compute_tax_amounts",
    )
    sale_tax_percent = fields.Float(
        string="% impuesto venta",
        compute="_compute_tax_percentages",
        digits=(16, 2),
    )

    sale_total = fields.Monetary(
        string="Precio con impuesto",
        currency_field="currency_id",
        compute="_compute_tax_amounts",
    )
    sale_total_with_canon = fields.Monetary(
        string="Venta + canon",
        currency_field="currency_id",
        compute="_compute_totals_with_canon",
    )
    purchase_history_html = fields.Html(
        string="Historial de compras",
        compute="_compute_histories",
        sanitize=False,
    )
    sale_history_html = fields.Html(
        string="Historial de ventas",
        compute="_compute_histories",
        sanitize=False,
    )

    @api.model
    def _default_stock_location_id(self):
        if not self._is_model_available("stock.warehouse") or not self._is_model_available("stock.location"):
            return False
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        if warehouse:
            return warehouse.lot_stock_id
        return self.env["stock.location"].search(
            [
                ("usage", "=", "internal"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    def _get_stock_location(self):
        self.ensure_one()
        location = self.stock_location_id
        if self._is_valid_stock_location_record(location):
            return location
        fallback_location = self._default_stock_location_id()
        return fallback_location if self._is_valid_stock_location_record(fallback_location) else False

    @api.model
    def _get_positive_rounding(self, rounding_value):
        try:
            rounding = float(rounding_value or 0.0)
        except (TypeError, ValueError):
            rounding = 0.0
        return rounding if rounding > 0.0 else 0.01

    @api.model
    def _is_valid_stock_location_record(self, location):
        if not location:
            return False
        if getattr(location, "_name", None) != "stock.location":
            return False
        exists_method = getattr(location, "exists", None)
        if callable(exists_method):
            return bool(location.exists())
        return False

    def _is_product_storable_for_stock(self):
        self.ensure_one()
        if "is_storable" in self._fields:
            return bool(self.is_storable)
        if self.type in ("consu", "product"):
            return True
        return bool(self.stock_initial_applied_qty or self.stock_initial_qty)

    def _ensure_stock_tracking_enabled(self):
        self.ensure_one()
        if "is_storable" in self._fields:
            self.is_storable = True
        elif "type" in self._fields and self.type == "consu":
            self.type = "product"

    @api.model
    def _get_available_quantity_safe(self, quant_model, variant, location):
        """Cantidad disponible robusta ante UoM mal configuradas (rounding <= 0)."""
        if not variant or not self._is_valid_stock_location_record(location):
            return 0.0
        try:
            return quant_model._get_available_quantity(variant, location, strict=True)
        except (AssertionError, AttributeError):
            quants = quant_model.search(
                [
                    ("product_id", "=", variant.id),
                    ("location_id", "=", location.id),
                ]
            )
            return sum(
                (quant.quantity or 0.0) - (getattr(quant, "reserved_quantity", 0.0) or 0.0)
                for quant in quants
            )

    def _get_single_variant(self):
        self.ensure_one()
        if self.product_variant_count > 1:
            raise ValidationError(
                _(
                    "Este formulario rapido solo admite productos sin variantes para ajustar stock."
                )
            )
        return self.product_variant_id

    def _compute_has_serial_number(self):
        for product in self:
            tracking_value = product.tracking if "tracking" in product._fields else "none"
            product.has_serial_number = tracking_value == "serial"

    @api.depends("serial_number_ids")
    def _compute_serial_number_count(self):
        for product in self:
            product.serial_number_count = len(product.serial_number_ids)

    @api.depends("piece_ids.price_unit")
    def _compute_piece_total_price(self):
        for product in self:
            product.piece_total_price = sum(product.piece_ids.mapped("price_unit"))

    @api.onchange("product_mode", "piece_ids", "piece_ids.price_unit")
    def _onchange_piece_prices(self):
        self._apply_piece_total_price()

    @api.onchange("product_business_type")
    def _onchange_product_business_type(self):
        for product in self:
            if product.product_business_type == "service":
                product.type = "service"
            else:
                if product.stock_initial_qty or product.stock_initial_applied_qty:
                    product.type = "product"
                else:
                    product.type = "consu"

    @api.onchange("type")
    def _onchange_type_to_business_type(self):
        for product in self:
            if product.type == "service":
                product.product_business_type = "service"
            elif product.product_business_type == "service":
                product.product_business_type = "goods"

    @api.onchange("has_imei")
    def _onchange_has_imei(self):
        for product in self:
            if not product.has_imei:
                product.imei_number = False

    def _inverse_has_serial_number(self):
        for product in self:
            if "tracking" not in product._fields:
                if not product.has_serial_number:
                    product.serial_number_input = False
                continue
            if product.has_serial_number:
                if "is_storable" in product._fields:
                    product.is_storable = True
                product.tracking = "serial"
            elif product.tracking == "serial":
                product.tracking = "none"
                product.serial_number_input = False

    @api.depends("stock_location_id", "type", "stock_initial_applied_qty")
    def _compute_stock_qty(self):
        if not self._is_model_available("stock.quant"):
            for product in self:
                product.stock_qty = 0.0
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if (
                not product.id
                or not product._is_product_storable_for_stock()
                or not product._is_valid_stock_location_record(location)
            ):
                product.stock_qty = 0.0
                continue
            variant = product.product_variant_id
            try:
                product.stock_qty = product._get_available_quantity_safe(
                    quant_model, variant, location
                )
            except Exception:
                product.stock_qty = 0.0

    @api.depends("type", "stock_initial_applied_qty")
    def _compute_stock_real_qty(self):
        for product in self:
            if not product.id or not product._is_product_storable_for_stock():
                product.stock_real_qty = 0.0
                continue
            variant = product.product_variant_id
            internal_qty_method = getattr(variant, "_get_internal_available_qty", None)
            if callable(internal_qty_method):
                product.stock_real_qty = float(internal_qty_method() or 0.0)
            else:
                product.stock_real_qty = float(getattr(variant, "qty_available", 0.0) or 0.0)

    @api.depends("product_business_type", "product_variant_ids")
    def _compute_service_sales_count(self):
        has_sale_line = self._is_model_available("sale.order.line")
        has_ot_line = self._is_model_available("helpdesk.ticket.ot.product.line")
        SaleOrderLine = self.env["sale.order.line"].sudo() if has_sale_line else False
        OTLine = self.env["helpdesk.ticket.ot.product.line"].sudo() if has_ot_line else False

        for product in self:
            product.service_sales_count = 0.0
            if (
                not product.id
                or product.product_business_type not in ("service", "software")
                or not product.product_variant_ids
            ):
                continue

            total_qty = 0.0

            if has_sale_line:
                sale_lines = SaleOrderLine.search(
                    [
                        ("product_id", "in", product.product_variant_ids.ids),
                        ("display_type", "=", False),
                        ("state", "in", ("sale", "done")),
                    ]
                )
                total_qty += sum(sale_lines.mapped("product_uom_qty"))

            if has_ot_line:
                ot_lines = OTLine.search(
                    [
                        ("product_id", "in", product.product_variant_ids.ids),
                        ("line_role", "=", "outgoing"),
                        ("ot_id.ot_type", "=", "external"),
                        ("ot_id.invoice_id", "!=", False),
                    ]
                )
                total_qty += sum(ot_lines.mapped("quantity"))

            product.service_sales_count = total_qty

    @api.depends("type", "stock_activity_period", "stock_initial_applied_qty")
    def _compute_stock_activity_summary(self):
        has_move_line = self._is_model_available("stock.move.line")
        MoveLine = self.env["stock.move.line"].sudo() if has_move_line else False
        today = fields.Date.context_today(self)

        for product in self:
            product.stock_in_today_qty = 0.0
            product.stock_out_today_qty = 0.0
            product.stock_last_move_at = False
            product.stock_last_move_ref = False

            if not has_move_line or not product.id or not product._is_product_storable_for_stock():
                continue

            period = product.stock_activity_period or "today"
            if period == "7d":
                start_date = today - timedelta(days=6)
            elif period == "30d":
                start_date = today - timedelta(days=29)
            else:
                start_date = today

            start_dt = fields.Datetime.to_datetime(f"{start_date} 00:00:00")
            end_dt = fields.Datetime.to_datetime(f"{today} 23:59:59") + timedelta(seconds=1)

            variant = product.product_variant_id
            day_lines = MoveLine.search(
                [
                    ("product_id", "=", variant.id),
                    ("date", ">=", start_dt),
                    ("date", "<", end_dt),
                    ("state", "=", "done"),
                ]
            )

            entries = 0.0
            exits = 0.0
            for line in day_lines:
                qty = float(
                    getattr(line, "quantity", 0.0)
                    or getattr(line, "qty_done", 0.0)
                    or getattr(line, "product_uom_qty", 0.0)
                )
                if qty <= 0.0:
                    continue
                src_internal = getattr(line.location_id, "usage", None) == "internal"
                dst_internal = getattr(line.location_dest_id, "usage", None) == "internal"
                if dst_internal and not src_internal:
                    entries += qty
                elif src_internal and not dst_internal:
                    exits += qty

            last_line = MoveLine.search(
                [
                    ("product_id", "=", variant.id),
                    ("state", "=", "done"),
                ],
                order="date desc, id desc",
                limit=1,
            )
            product.stock_in_today_qty = entries
            product.stock_out_today_qty = exits
            product.stock_last_move_at = last_line.date if last_line else False
            product.stock_last_move_ref = (
                last_line.reference
                or (last_line.move_id.reference if last_line and last_line.move_id else False)
                or (last_line.picking_id.name if last_line and last_line.picking_id else False)
            )

    @api.depends("stock_qty", "stock_location_id", "type")
    def _compute_stock_sync_status(self):
        if not self._is_model_available("stock.quant"):
            for product in self:
                product.stock_sync_status = "unavailable"
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if (
                not product.id
                or not product._is_product_storable_for_stock()
                or not product._is_valid_stock_location_record(location)
            ):
                product.stock_sync_status = "unavailable"
                continue
            variant = product.product_variant_id
            precision_rounding = product._get_positive_rounding(
                getattr(variant.uom_id, "rounding", None)
            )
            real_qty = product._get_available_quantity_safe(quant_model, variant, location)
            target_qty = float(product.stock_qty or 0.0)
            product.stock_sync_status = (
                "synced"
                if float_is_zero(target_qty - real_qty, precision_rounding=precision_rounding)
                else "pending"
            )

    def _inverse_stock_qty(self):
        if not self._is_model_available("stock.quant"):
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if not product._is_valid_stock_location_record(location):
                continue
            variant = product._get_single_variant()
            target_qty = float(product.stock_qty or 0.0)
            precision_rounding = product._get_positive_rounding(
                getattr(variant.uom_id, "rounding", None)
            )
            product._validate_target_stock_quantity(target_qty, precision_rounding)
            product._ensure_stock_tracking_enabled()

            current_qty = product._get_available_quantity_safe(
                quant_model,
                variant,
                location,
            )
            delta_qty = target_qty - current_qty
            if float_is_zero(delta_qty, precision_rounding=precision_rounding):
                continue
            quant_model._update_available_quantity(variant, location, quantity=delta_qty)
            product.stock_last_synced_at = fields.Datetime.now()

    def _validate_target_stock_quantity(self, target_qty, precision_rounding):
        tracking_value = self.tracking if "tracking" in self._fields else "none"
        if tracking_value == "serial" and float_compare(
            target_qty,
            round(target_qty),
            precision_rounding=precision_rounding,
        ):
            raise ValidationError(
                _("Los productos con numero de serie solo admiten cantidades enteras.")
            )

    def _inverse_stock_initial_qty(self):
        if not self._is_model_available("stock.quant"):
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if not product._is_valid_stock_location_record(location):
                continue
            variant = product._get_single_variant()
            target_initial_qty = float(product.stock_initial_qty or 0.0)
            # Obtener precision_rounding seguro
            precision_rounding = product._get_positive_rounding(
                getattr(variant.uom_id, "rounding", None)
            )
            product._validate_target_stock_quantity(target_initial_qty, precision_rounding)
            product._ensure_stock_tracking_enabled()

            previous_applied = float(product.stock_initial_applied_qty or 0.0)
            if product.stock_initial_locked and not float_is_zero(
                target_initial_qty - previous_applied,
                precision_rounding=precision_rounding,
            ):
                raise ValidationError(
                    _(
                        "El stock inicial ya fue aplicado. A partir de ahora ajusta el 'Stock actual'."
                    )
                )
            delta_qty = target_initial_qty - previous_applied
            if float_is_zero(delta_qty, precision_rounding=precision_rounding):
                continue
            quant_model._update_available_quantity(variant, location, quantity=delta_qty)
            product.stock_initial_applied_qty = target_initial_qty
            if not float_is_zero(target_initial_qty, precision_rounding=precision_rounding):
                product.stock_initial_locked = True
            product.stock_last_synced_at = fields.Datetime.now()

    def _apply_stock_sync_from_values(self, vals):
        """Sincroniza inventario cuando el formulario envía campos de stock."""
        if not vals:
            return
        if "stock_initial_qty" in vals:
            self._inverse_stock_initial_qty()

    def action_open_inventory_quants(self):
        self.ensure_one()
        if not self._is_model_available("stock.quant"):
            raise ValidationError(_("El módulo de Inventario no está disponible."))
        action = self.env.ref("stock.quantsact", raise_if_not_found=False)
        if not action:
            raise ValidationError(_("No se ha encontrado la acción de inventario de quants."))

        return {
            **action.read()[0],
            "domain": [("product_id", "=", self.product_variant_id.id)],
            "context": {
                "search_default_internal_loc": 1,
                "default_product_id": self.product_variant_id.id,
            },
        }


    @api.depends("standard_price", "purchase_tax_amount", "canon_amount", "list_price", "sale_tax_amount")
    def _compute_totals_with_canon(self):
        for product in self:
            base_purchase = product.standard_price or 0.0
            tax_purchase = product.purchase_tax_amount or 0.0
            canon = product.canon_amount or 0.0
            product.purchase_total_with_canon = base_purchase + tax_purchase + canon

            base_sale = product.list_price or 0.0
            tax_sale = product.sale_tax_amount or 0.0
            product.sale_total_with_canon = base_sale + tax_sale + canon

    @api.depends(
        "standard_price",
        "list_price",
        "supplier_taxes_id",
        "taxes_id",
        "company_id",
        "currency_id",
        "cost_currency_id",
    )
    def _compute_tax_amounts(self):
        for product in self:
            purchase_base = product.standard_price or 0.0
            sale_base = product.list_price or 0.0

            purchase_currency = product.cost_currency_id or product.currency_id
            sale_currency = product.currency_id

            purchase_vals = product._compute_price_taxes(
                purchase_base,
                product.supplier_taxes_id,
                purchase_currency,
            )
            sale_vals = product._compute_price_taxes(
                sale_base,
                product.taxes_id,
                sale_currency,
            )

            product.purchase_tax_amount = purchase_vals["tax_amount"]
            product.purchase_total = purchase_vals["total"]
            product.sale_tax_amount = sale_vals["tax_amount"]
            product.sale_total = sale_vals["total"]

    def _safe_percent_from_taxes(self, taxes, tax_use):
        """Devuelve suma de impuestos % y evita romper si hay registros temporales en formulario."""
        percent = 0.0
        try:
            percent = sum(
                tax.amount
                for tax in taxes
                if getattr(tax, "amount_type", False) == "percent"
            )
        except Exception:
            percent = 0.0

        if percent:
            return percent
        # Si no hay impuestos aplicados, no forzar 21% en pantalla.
        return 0.0

    @api.depends(
        "standard_price",
        "list_price",
        "purchase_tax_amount",
        "sale_tax_amount",
        "supplier_taxes_id",
        "taxes_id",
    )
    def _compute_tax_percentages(self):
        for product in self:
            purchase_base = product.standard_price or 0.0
            sale_base = product.list_price or 0.0

            purchase_percent_from_taxes = product._safe_percent_from_taxes(
                product.supplier_taxes_id, "purchase"
            )
            sale_percent_from_taxes = product._safe_percent_from_taxes(
                product.taxes_id, "sale"
            )

            product.purchase_tax_percent = (
                (product.purchase_tax_amount / purchase_base) * 100.0
                if purchase_base
                else purchase_percent_from_taxes
            )
            product.sale_tax_percent = (
                (product.sale_tax_amount / sale_base) * 100.0
                if sale_base
                else sale_percent_from_taxes
            )

    @api.onchange("supplier_taxes_id", "taxes_id")
    def _onchange_catalog_taxes_filter(self):
        # No tocar valores en onchange: algunos clientes web envían registros temporales
        # y filtrar aquí puede provocar que desaparezcan visualmente tras guardar.
        return

    @api.model
    def _extract_tax_ids_from_m2m_value(self, raw_value):
        """Extrae IDs válidos de un valor M2M (ids/comandos) de forma robusta."""
        if not raw_value:
            return [], False

        valid_ids = []
        explicit_clear = False

        if hasattr(raw_value, "ids"):
            valid_ids.extend([rid for rid in raw_value.ids if isinstance(rid, int) and rid > 0])
            return list(dict.fromkeys(valid_ids)), False

        commands = raw_value if isinstance(raw_value, (list, tuple)) else [raw_value]
        for cmd in commands:
            if hasattr(cmd, "id"):
                if isinstance(cmd.id, int) and cmd.id > 0:
                    valid_ids.append(cmd.id)
                continue

            if isinstance(cmd, int):
                if cmd > 0:
                    valid_ids.append(cmd)
                continue

            if not isinstance(cmd, (list, tuple)) or not cmd:
                continue

            command_type = cmd[0]
            if command_type == 5:
                explicit_clear = True
                continue

            if command_type in (1, 2, 3, 4):
                if len(cmd) >= 2:
                    record_id = cmd[1]
                    if hasattr(record_id, "id"):
                        record_id = record_id.id
                    if isinstance(record_id, str) and record_id.isdigit():
                        record_id = int(record_id)
                    if isinstance(record_id, int) and record_id > 0:
                        valid_ids.append(record_id)
                continue

            if command_type == 6 and len(cmd) >= 3 and isinstance(cmd[2], (list, tuple)):
                if len(cmd[2]) == 0:
                    explicit_clear = True
                for record_id in cmd[2]:
                    if hasattr(record_id, "id"):
                        record_id = record_id.id
                    if isinstance(record_id, str) and record_id.isdigit():
                        record_id = int(record_id)
                    if isinstance(record_id, int) and record_id > 0:
                        valid_ids.append(record_id)

        return list(dict.fromkeys(valid_ids)), explicit_clear

    @api.constrains("supplier_taxes_id", "taxes_id")
    def _check_catalog_taxes_filter(self):
        for product in self:
            if (
                product.supplier_taxes_id
                and "type_tax_use" in product.supplier_taxes_id._fields
                and any(tax.type_tax_use != "purchase" for tax in product.supplier_taxes_id)
            ):
                raise ValidationError(
                    _("Los impuestos de compra solo pueden tener tipo de uso 'purchase'.")
                )
            if (
                product.taxes_id
                and "type_tax_use" in product.taxes_id._fields
                and any(tax.type_tax_use != "sale" for tax in product.taxes_id)
            ):
                raise ValidationError(
                    _("Los impuestos de venta solo pueden tener tipo de uso 'sale'.")
                )

    def _compute_histories(self):
        has_purchase_model = self._is_model_available("purchase.order.line")
        has_sale_model = self._is_model_available("sale.order.line")
        purchase_lines_model = self.env["purchase.order.line"].sudo() if has_purchase_model else False
        sale_lines_model = self.env["sale.order.line"].sudo() if has_sale_model else False
        for product in self:
            if not product.id:
                product.purchase_history_html = product._empty_history_html("Sin compras registradas.")
                product.sale_history_html = product._empty_history_html("Sin ventas registradas.")
                continue
            if has_purchase_model:
                purchase_anchor_lines = purchase_lines_model.search(
                    [
                        ("product_id.product_tmpl_id", "=", product.id),
                        ("display_type", "=", False),
                        ("state", "in", ("draft", "sent", "to approve", "purchase", "done", "cancel")),
                    ],
                    order="id desc",
                    limit=80,
                )

                purchase_orders = purchase_anchor_lines.mapped("order_id").sorted(
                    key=lambda order: (order.date_order or fields.Datetime.from_string("1970-01-01 00:00:00"), order.id),
                    reverse=True,
                )[:10]

                purchase_lines = purchase_lines_model.search(
                    [
                        ("order_id", "in", purchase_orders.ids),
                        ("display_type", "=", False),
                    ],
                    order="id desc",
                    limit=300,
                ).sorted(
                    key=lambda line: (
                        line.order_id.date_order or fields.Datetime.from_string("1970-01-01 00:00:00"),
                        line.order_id.id,
                        line.id,
                    ),
                    reverse=True,
                )

                product.purchase_history_html = product._format_history_html(
                    purchase_lines, "Sin compras registradas."
                )
            else:
                product.purchase_history_html = product._empty_history_html("Sin compras registradas.")

            if has_sale_model:
                sale_lines = sale_lines_model.search(
                    [
                        ("product_id.product_tmpl_id", "=", product.id),
                        ("display_type", "=", False),
                        ("state", "in", ("draft", "sent", "sale", "done", "cancel")),
                    ],
                    order="id desc",
                    limit=80,
                )
                sale_lines = sale_lines.sorted(
                    key=lambda line: (line.order_id.date_order or fields.Datetime.from_string("1970-01-01 00:00:00"), line.id),
                    reverse=True,
                )[:10]
                product.sale_history_html = product._format_history_html(
                    sale_lines, "Sin ventas registradas."
                )
            else:
                product.sale_history_html = product._empty_history_html("Sin ventas registradas.")

    def action_save_product_record(self):
        self.ensure_one()
        pieces_added = self._sync_pending_pieces()
        self._apply_piece_total_price()
        serials_added = self._sync_pending_serial_numbers()

        detail_parts = []
        if pieces_added:
            detail_parts.append(_("Piezas añadidas: %s") % pieces_added)
        if serials_added:
            detail_parts.append(_("Números de serie añadidos: %s") % serials_added)
        detail_suffix = f" {' | '.join(detail_parts)}" if detail_parts else ""

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Producto guardado"),
                "message": _("Los cambios del producto se han guardado correctamente.") + detail_suffix,
                "type": "success",
                "sticky": False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        install_mode = bool(self.env.context.get("install_mode"))
        has_account_tax = self._is_model_available("account.tax")
        stock_sync_map = []
        for vals in vals_list:
            stock_sync_map.append(
                {
                    "stock_initial_qty": vals.get("stock_initial_qty") if "stock_initial_qty" in vals else None,
                }
            )
            if (
                vals.get("stock_location_id")
                and not vals.get("company_id")
                and self._is_model_available("stock.location")
            ):
                location = self.env["stock.location"].browse(vals["stock_location_id"])
                vals["company_id"] = location.company_id.id or self.env.company.id

            if install_mode:
                continue

            for many2many_field in ("supplier_taxes_id", "taxes_id"):
                if many2many_field not in vals:
                    continue

                # Si el modelo de impuestos no está disponible, limpiar para evitar _unknown.
                if not has_account_tax:
                    vals[many2many_field] = False
                    continue

                raw_value = vals[many2many_field]
                if not raw_value:
                    vals[many2many_field] = False
                    continue

                valid_ids = []

                try:
                    if hasattr(raw_value, "ids"):
                        valid_ids.extend(
                            [rid for rid in raw_value.ids if isinstance(rid, int) and rid > 0]
                        )
                    else:
                        commands = raw_value if isinstance(raw_value, (list, tuple)) else [raw_value]
                        for cmd in commands:
                            if hasattr(cmd, "id"):
                                if isinstance(cmd.id, int) and cmd.id > 0:
                                    valid_ids.append(cmd.id)
                                continue

                            if isinstance(cmd, int):
                                if cmd > 0:
                                    valid_ids.append(cmd)
                                continue

                            if not isinstance(cmd, (list, tuple)) or not cmd:
                                continue

                            command_type = cmd[0]
                            if command_type in (1, 2, 3, 4):
                                if len(cmd) >= 2:
                                    record_id = cmd[1]
                                    if hasattr(record_id, "id"):
                                        record_id = record_id.id
                                    if isinstance(record_id, str) and record_id.isdigit():
                                        record_id = int(record_id)
                                    if isinstance(record_id, int) and record_id > 0:
                                        valid_ids.append(record_id)
                            elif command_type == 6:
                                if len(cmd) >= 3 and isinstance(cmd[2], (list, tuple)):
                                    for record_id in cmd[2]:
                                        if hasattr(record_id, "id"):
                                            record_id = record_id.id
                                        if isinstance(record_id, str) and record_id.isdigit():
                                            record_id = int(record_id)
                                        if isinstance(record_id, int) and record_id > 0:
                                            valid_ids.append(record_id)
                except Exception:
                    # No tocar el valor original si no podemos normalizarlo.
                    continue

                clean_ids = list(dict.fromkeys(valid_ids))
                if clean_ids:
                    vals[many2many_field] = [(6, 0, clean_ids)]
                # Si no pudimos extraer IDs válidos, mantener el valor original
                # para que el ORM procese correctamente comandos nativos.


            if "taxes_id" not in vals:
                sale_tax = self._default_sale_taxes()
                if sale_tax:
                    vals["taxes_id"] = [(6, 0, sale_tax.ids)]
            if "supplier_taxes_id" not in vals:
                purchase_tax = self._default_purchase_taxes()
                if purchase_tax:
                    vals["supplier_taxes_id"] = [(6, 0, purchase_tax.ids)]

        products = super().create(vals_list)
        products._sync_pending_pieces()
        products._apply_piece_total_price()
        products._sync_pending_serial_numbers()
        if not install_mode:
            for product, stock_sync_vals in zip(products, stock_sync_map):
                product._apply_stock_sync_from_values(stock_sync_vals)
        return products

    def write(self, vals):
        # Solo tocar impuestos si el usuario los envía explícitamente
        if vals and self._is_model_available("account.tax"):
            for many2many_field in ("supplier_taxes_id", "taxes_id"):
                if many2many_field in vals:
                    raw_value = vals[many2many_field]
                    # Si es explícitamente False/None, permitir limpieza
                    if raw_value is False or raw_value is None:
                        vals[many2many_field] = False
                        continue
                    # Si es lista/tuple vacía, es limpieza explícita
                    if isinstance(raw_value, (list, tuple)) and not raw_value:
                        vals[many2many_field] = False
                        continue
                    try:
                        clean_ids, explicit_clear = self._extract_tax_ids_from_m2m_value(raw_value)
                    except Exception:
                        clean_ids, explicit_clear = [], False
                    if clean_ids:
                        vals[many2many_field] = [(6, 0, clean_ids)]
                    elif explicit_clear:
                        vals[many2many_field] = False
                    else:
                        # Si no hay IDs válidos ni vaciado explícito, no tocar impuestos existentes.
                        vals.pop(many2many_field, None)
        # Solo tocar proveedor si el usuario lo envía explícitamente
        if "supplier_partner_id" in vals:
            raw_value = vals["supplier_partner_id"]
            if raw_value and not isinstance(raw_value, (int, list, tuple)):
                if hasattr(raw_value, "id"):
                    vals["supplier_partner_id"] = raw_value.id
                elif isinstance(raw_value, (list, tuple)) and raw_value:
                    if isinstance(raw_value[0], int) and raw_value[0] in (4, 1, 2, 3):
                        if len(raw_value) > 1:
                            vals["supplier_partner_id"] = raw_value[1]
                        else:
                            vals.pop("supplier_partner_id", None)
                    elif isinstance(raw_value[0], int) and raw_value[0] > 0:
                        vals["supplier_partner_id"] = raw_value[0]

        if "has_imei" in vals and not vals.get("has_imei"):
            vals["imei_number"] = False
        if vals.get("stock_location_id") and self._is_model_available("stock.location"):
            location = self.env["stock.location"].browse(vals["stock_location_id"])
            location_company_id = location.company_id.id if location else False
            if not vals.get("company_id"):
                vals["company_id"] = location_company_id or self.env.company.id
        result = super().write(vals)
        self._apply_stock_sync_from_values(vals)
        if "piece_input" in vals or "piece_product_id" in vals or "product_mode" in vals:
            self._sync_pending_pieces()
        if "piece_ids" in vals or "piece_input" in vals or "piece_product_id" in vals or "product_mode" in vals:
            self._apply_piece_total_price()
        if "serial_number_input" in vals or "has_serial_number" in vals:
            self._sync_pending_serial_numbers()
        return result

    def _sync_pending_pieces(self):
        piece_model = self.env["product.template.piece"]
        created_count = 0
        for product in self:
            if product.product_mode != "pieces":
                continue
            piece_values = product._parse_piece_values(product.piece_input)
            if product.piece_product_id and product.piece_product_id != product:
                piece_values.append(product.piece_product_id.display_name or product.piece_product_id.name)
            if not piece_values:
                continue
            created_pieces = piece_model.create(
                [{"product_tmpl_id": product.id, "name": piece_value} for piece_value in piece_values]
            )
            created_count += len(created_pieces)
            super(Product, product).write({"piece_input": False, "piece_product_id": False})
        return created_count

    def _apply_piece_total_price(self):
        for product in self:
            if product.product_mode != "pieces":
                continue
            piece_prices = product.piece_ids.mapped("price_unit")
            if not piece_prices or not any(price not in (False, None, 0.0) for price in piece_prices):
                continue
            product.standard_price = product.piece_total_price

    @api.constrains("product_mode", "stock_qty")
    def _check_product_mode_qty(self):
        for product in self:
            if (
                product.product_mode == "single"
                and float_compare(
                    product.stock_qty,
                    1.0,
                    precision_rounding=product._get_positive_rounding(product.uom_id.rounding),
                ) > 0
            ):
                raise ValidationError(
                    _("Los productos unicos solo pueden tener una unidad en stock.")
                )

    @api.constrains("has_imei", "imei_number")
    def _check_imei_number(self):
        for product in self:
            if not product.has_imei:
                continue
            imei = (product.imei_number or "").strip()
            if not imei:
                raise ValidationError(
                    _("Debes indicar el IMEI cuando la casilla 'Tiene IMEI' esté marcada.")
                )
            normalized_imei = imei.replace(" ", "")
            if not normalized_imei.isdigit() or len(normalized_imei) != 15:
                raise ValidationError(
                    _("El IMEI debe contener exactamente 15 dígitos numéricos.")
                )
            product.imei_number = normalized_imei

    @api.constrains(
        "has_serial_number",
        "serial_number_input",
        "serial_number_ids",
    )
    def _check_serial_number(self):
        for product in self:
            if (
                product.has_serial_number
                and not product.serial_number_input
                and not product.serial_number_ids
            ):
                raise ValidationError(
                    _("Debes indicar el numero de serie cuando la casilla este marcada.")
                )

    def _sync_pending_serial_numbers(self):
        serial_model = self.env["product.template.serial.number"]
        created_count = 0
        for product in self:
            if not product.has_serial_number or not product.serial_number_input:
                continue
            serial_values = product._parse_serial_numbers(product.serial_number_input)
            existing_serials = set(product.serial_number_ids.mapped("name"))
            duplicate_serials = sorted(existing_serials.intersection(serial_values))
            if duplicate_serials:
                raise ValidationError(
                    _(
                        "Los siguientes numeros de serie ya existen en este producto: %s"
                    )
                    % ", ".join(duplicate_serials)
                )
            created_serials = serial_model.create(
                [{"product_tmpl_id": product.id, "name": serial_value} for serial_value in serial_values]
            )
            created_count += len(created_serials)
            super(Product, product).write({"serial_number_input": False})
        return created_count

    @api.model
    def _parse_serial_numbers(self, serial_text):
        raw_chunks = (serial_text or "").replace(";", "\n").replace(",", "\n").splitlines()
        serial_values = []
        for chunk in raw_chunks:
            serial_value = chunk.strip()
            if not serial_value:
                continue
            if serial_value in serial_values:
                raise ValidationError(
                    _("No puedes guardar numeros de serie duplicados en la misma entrada.")
                )
            serial_values.append(serial_value)
        return serial_values

    @api.model
    def _parse_piece_values(self, piece_text):
        raw_chunks = (piece_text or "").replace(";", "\n").replace(",", "\n").splitlines()
        piece_values = []
        for chunk in raw_chunks:
            piece_value = chunk.strip()
            if not piece_value:
                continue
            piece_values.append(piece_value)
        return piece_values

    def _compute_price_taxes(self, base_amount, taxes, currency):
        self.ensure_one()
        base_amount = base_amount or 0.0
        if not taxes:
            return {"tax_amount": 0.0, "total": base_amount}
        if not hasattr(taxes, "compute_all"):
            return {"tax_amount": 0.0, "total": base_amount}
        if "company_id" in taxes._fields:
            taxes = taxes.filtered(
                lambda tax: not tax.company_id
                or tax.company_id == (self.company_id or self.env.company)
            )
        if not taxes:
            return {"tax_amount": 0.0, "total": base_amount}
        variant = self.product_variant_id
        tax_res = taxes.compute_all(
            base_amount,
            currency=currency,
            quantity=1.0,
            product=variant,
            partner=False,
        )
        return {
            "tax_amount": tax_res["total_included"] - tax_res["total_excluded"],
            "total": tax_res["total_included"],
        }

    def _format_history_html(self, lines, empty_message):
        if not lines:
            return self._empty_history_html(empty_message)

        is_purchase_history = lines and lines[0]._name == "purchase.order.line"
        if is_purchase_history:
            return self._format_purchase_history_html(lines)

        show_variant_info = any(
            getattr(line.product_id.product_tmpl_id, "product_variant_count", 0) > 1
            for line in lines
            if getattr(line, "product_id", False)
        )
        items = []
        subtotal_total = 0.0
        tax_total = 0.0
        grand_total = 0.0
        currency_label = ""
        for line in lines:
            if line._name == "purchase.order.line":
                date_value = line.order_id.date_order
                partner_name = line.partner_id.display_name
                quantity = line.product_qty
                currency = line.currency_id or line.company_id.currency_id
            else:
                date_value = line.order_id.date_order
                partner_name = line.order_partner_id.display_name
                quantity = line.product_uom_qty
                currency = line.currency_id or line.company_id.currency_id
            subtotal = line.price_subtotal
            total = line.price_total
            tax_amount = total - subtotal
            subtotal_total += subtotal
            tax_total += tax_amount
            grand_total += total
            date_label = date_value.strftime("%d/%m/%Y") if date_value else "Sin fecha"
            partner_label = escape(partner_name or "Sin contacto")
            currency_label = escape(currency.name or "")
            variant_line = (
                f"<strong>Variante:</strong> {escape(line.product_id.display_name or line.product_id.name or 'N/A')}<br/>"
                if show_variant_info
                else ""
            )
            items.append(
                "<li class='mb-2'>"
                f"<strong>{escape(date_label)}</strong> - {partner_label}<br/>"
                f"{variant_line}"
                f"{quantity:.2f} x {line.price_unit:.2f} {currency_label}<br/>"
                f"Base: {subtotal:.2f} {currency_label} | Impuesto: {tax_amount:.2f} {currency_label} | Total: {total:.2f} {currency_label}"
                "</li>"
            )

        totals_html = (
            "<div class='mb-3'>"
            f"<strong>Base:</strong> {subtotal_total:.2f} {currency_label}"
            f"<br/><strong>Impuestos:</strong> {tax_total:.2f} {currency_label}"
            f"<br/><strong>Total:</strong> {grand_total:.2f} {currency_label}"
            "</div>"
        )
        return f"{totals_html}<ul class='mb-0'>{''.join(items)}</ul>"

    def _format_purchase_history_html(self, lines):
        if not lines:
            return self._empty_history_html("Sin compras registradas.")

        lines_by_order = {}
        sorted_order_ids = []
        for line in lines:
            order = line.order_id
            if not order:
                continue
            if order.id not in lines_by_order:
                lines_by_order[order.id] = []
                sorted_order_ids.append(order.id)
            lines_by_order[order.id].append(line)

        if not sorted_order_ids:
            return self._empty_history_html("Sin compras registradas.")

        overall_base = 0.0
        overall_canon = 0.0
        overall_tax = 0.0
        overall_total = 0.0
        global_currency_label = ""
        order_blocks = []

        for order_id in sorted_order_ids:
            order_lines = lines_by_order[order_id]
            if not order_lines:
                continue

            order = order_lines[0].order_id
            date_value = order.date_order
            date_label = date_value.strftime("%d/%m/%Y") if date_value else "Sin fecha"
            partner_name = escape(order.partner_id.display_name or "Sin contacto")

            line_rows = []
            order_base = 0.0
            order_canon = 0.0
            order_tax = 0.0
            order_total = 0.0
            order_currency_label = ""

            sorted_order_lines = sorted(
                order_lines,
                key=lambda line: (line.id,),
                reverse=False,
            )

            for line in sorted_order_lines:
                quantity = line.product_qty or 0.0
                unit_price = line.price_unit or 0.0
                subtotal = line.price_subtotal or 0.0
                total = line.price_total or 0.0
                tax_amount = total - subtotal

                canon_unit = line.product_id.product_tmpl_id.canon_amount or 0.0
                canon_total = canon_unit * quantity
                final_total = total + canon_total

                currency = line.currency_id or line.company_id.currency_id
                currency_label = escape(currency.name or "")
                order_currency_label = currency_label
                if not global_currency_label:
                    global_currency_label = currency_label

                product_name = escape(line.product_id.display_name or line.name or "Producto")

                order_base += subtotal
                order_canon += canon_total
                order_tax += tax_amount
                order_total += final_total

                line_rows.append(
                    "<li class='mb-2'>"
                    f"<strong>{product_name}</strong><br/>"
                    f"{quantity:.2f} x {unit_price:.2f} {currency_label}<br/>"
                    f"Base: {subtotal:.2f} {currency_label} | Canon: {canon_total:.2f} {currency_label} | Impuesto: {tax_amount:.2f} {currency_label} | Total: {final_total:.2f} {currency_label}"
                    "</li>"
                )

            overall_base += order_base
            overall_canon += order_canon
            overall_tax += order_tax
            overall_total += order_total

            order_blocks.append(
                "<div class='mb-3'>"
                f"<strong>{escape(date_label)}</strong> - {partner_name}<br/>"
                f"<ul class='mb-2'>{''.join(line_rows)}</ul>"
                f"<strong>Total base pedido:</strong> {order_base:.2f} {order_currency_label}"
                f"<br/><strong>Total canon pedido:</strong> {order_canon:.2f} {order_currency_label}"
                f"<br/><strong>Total impuestos pedido:</strong> {order_tax:.2f} {order_currency_label}"
                f"<br/><strong>Total pedido:</strong> {order_total:.2f} {order_currency_label}"
                "</div>"
            )

        overall_totals_html = (
            "<div class='mb-3'>"
            f"<strong>Total base:</strong> {overall_base:.2f} {global_currency_label}"
            f"<br/><strong>Total canon:</strong> {overall_canon:.2f} {global_currency_label}"
            f"<br/><strong>Total impuestos:</strong> {overall_tax:.2f} {global_currency_label}"
            f"<br/><strong>Total final:</strong> {overall_total:.2f} {global_currency_label}"
            "</div>"
        )

        return f"{overall_totals_html}{''.join(order_blocks)}"

    @staticmethod
    def _empty_history_html(message):
        return f"<p class='text-muted mb-0'>{escape(message)}</p>"
