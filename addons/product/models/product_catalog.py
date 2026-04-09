from markupsafe import escape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class Product(models.Model):
    _inherit = "product.template"

    @api.model
    def _default_21_tax(self, tax_use):
        if not self._is_model_available("account.tax"):
            return False
        tax = self.env["account.tax"].search(
            [
                ("type_tax_use", "=", tax_use),
                ("amount_type", "=", "percent"),
                ("amount", "=", 21.0),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        return tax or False

    @api.model
    def _default_sale_taxes(self):
        tax_21 = self._default_21_tax("sale")
        if tax_21:
            return tax_21
        if not self._is_model_available("account.tax"):
            return False
        companies = self.env.companies
        if "account_sale_tax_id" in companies._fields and companies.account_sale_tax_id:
            return companies.account_sale_tax_id
        root_company = companies.root_id.sudo() if companies.root_id else False
        if root_company and "account_sale_tax_id" in root_company._fields:
            return root_company.account_sale_tax_id
        return False

    @api.model
    def _default_purchase_taxes(self):
        tax_21 = self._default_21_tax("purchase")
        if tax_21:
            return tax_21
        if not self._is_model_available("account.tax"):
            return False
        companies = self.env.companies
        if "account_purchase_tax_id" in companies._fields and companies.account_purchase_tax_id:
            return companies.account_purchase_tax_id
        root_company = companies.root_id.sudo() if companies.root_id else False
        if root_company and "account_purchase_tax_id" in root_company._fields:
            return root_company.account_purchase_tax_id
        return False

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
        return model_name in self.env.registry

    def init(self):
        """Autocura de esquema para instalaciones donde el upgrade de módulo quedó a medias.

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
                ADD COLUMN IF NOT EXISTS purchase_tax_percent numeric,
                ADD COLUMN IF NOT EXISTS sale_tax_percent numeric,
                ADD COLUMN IF NOT EXISTS piece_input varchar,
                ADD COLUMN IF NOT EXISTS piece_product_id integer,
                ADD COLUMN IF NOT EXISTS serial_number_input varchar,
                ADD COLUMN IF NOT EXISTS supplier_partner_id integer,
                ADD COLUMN IF NOT EXISTS supplier_reference text,
                ADD COLUMN IF NOT EXISTS stock_location_id integer
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
        inverse="_inverse_stock_qty",
        digits="Product Unit of Measure",
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
        return self.stock_location_id or self._default_stock_location_id()

    @api.model
    def _get_positive_rounding(self, rounding_value):
        try:
            rounding = float(rounding_value or 0.0)
        except (TypeError, ValueError):
            rounding = 0.0
        return rounding if rounding > 0.0 else 0.01

    @api.model
    def _get_available_quantity_safe(self, quant_model, variant, location):
        """Cantidad disponible robusta ante UoM mal configuradas (rounding <= 0)."""
        if not variant or not location:
            return 0.0
        try:
            return quant_model._get_available_quantity(variant, location, strict=True)
        except AssertionError:
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
                product.type = "consu"

    @api.onchange("type")
    def _onchange_type_to_business_type(self):
        for product in self:
            if product.type == "service":
                product.product_business_type = "service"
            elif product.product_business_type == "service":
                product.product_business_type = "goods"

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

    def _compute_stock_qty(self):
        if not self._is_model_available("stock.quant"):
            for product in self:
                product.stock_qty = 0.0
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if not product.id or not location or not product.is_storable:
                product.stock_qty = 0.0
                continue
            variant = product.product_variant_id
            product.stock_qty = product._get_available_quantity_safe(
                quant_model, variant, location
            )

    def _inverse_stock_qty(self):
        if not self._is_model_available("stock.quant"):
            return
        quant_model = self.env["stock.quant"].sudo()
        for product in self:
            location = product._get_stock_location()
            if not location:
                continue
            variant = product._get_single_variant()
            target_qty = product.stock_qty
            # Obtener precision_rounding seguro
            precision_rounding = product._get_positive_rounding(
                getattr(variant.uom_id, "rounding", None)
            )
            if product.product_mode == "single" and float_compare(
                target_qty,
                1.0,
                precision_rounding=precision_rounding,
            ) > 0:
                raise ValidationError(
                    _(
                        "Los productos unicos solo admiten una unidad en stock."
                    )
                )
            tracking_value = product.tracking if "tracking" in product._fields else "none"
            if tracking_value == "serial" and float_compare(
                target_qty,
                round(target_qty),
                precision_rounding=precision_rounding,
            ):
                raise ValidationError(
                    _(
                        "Los productos con numero de serie solo admiten cantidades enteras."
                    )
                )
            if "is_storable" in product._fields:
                product.is_storable = True
            current_qty = product._get_available_quantity_safe(
                quant_model, variant, location
            )
            delta_qty = target_qty - current_qty
            if float_is_zero(delta_qty, precision_rounding=precision_rounding):
                continue
            quant_model._update_available_quantity(variant, location, quantity=delta_qty)


    @api.depends("purchase_total", "sale_total", "canon_amount")
    def _compute_totals_with_canon(self):
        for product in self:
            canon = product.canon_amount or 0.0
            product.purchase_total_with_canon = (product.purchase_total or 0.0) + canon
            product.sale_total_with_canon = (product.sale_total or 0.0) + canon

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

        default_tax = self._default_21_tax(tax_use)
        return float(getattr(default_tax, "amount", 0.0) or 0.0)

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
        for product in self:
            if product.supplier_taxes_id and "type_tax_use" in product.supplier_taxes_id._fields:
                product.supplier_taxes_id = product.supplier_taxes_id.filtered(
                    lambda tax: tax.type_tax_use == "purchase"
                )
            if product.taxes_id and "type_tax_use" in product.taxes_id._fields:
                product.taxes_id = product.taxes_id.filtered(
                    lambda tax: tax.type_tax_use == "sale"
                )

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
        purchase_lines_model = self.env["purchase.order.line"].sudo() if self._is_model_available("purchase.order.line") else False
        sale_lines_model = self.env["sale.order.line"].sudo() if self._is_model_available("sale.order.line") else False
        for product in self:
            if not purchase_lines_model or not sale_lines_model:
                product.purchase_history_html = product._empty_history_html("Sin compras registradas.")
                product.sale_history_html = product._empty_history_html("Sin ventas registradas.")
                continue
            if not product.id:
                product.purchase_history_html = product._empty_history_html("Sin compras registradas.")
                product.sale_history_html = product._empty_history_html("Sin ventas registradas.")
                continue
            purchase_lines = purchase_lines_model.search(
                [
                    ("product_id.product_tmpl_id", "=", product.id),
                    ("display_type", "=", False),
                    ("state", "in", ("to approve", "purchase", "done")),
                ],
                order="id desc",
                limit=80,
            )
            purchase_lines = purchase_lines.sorted(
                key=lambda line: (line.date_order or fields.Datetime.from_string("1970-01-01 00:00:00"), line.id),
                reverse=True,
            )[:10]
            sale_lines = sale_lines_model.search(
                [
                    ("product_id.product_tmpl_id", "=", product.id),
                    ("display_type", "=", False),
                    ("state", "in", ("sale", "done")),
                ],
                order="id desc",
                limit=80,
            )
            sale_lines = sale_lines.sorted(
                key=lambda line: (line.order_id.date_order or fields.Datetime.from_string("1970-01-01 00:00:00"), line.id),
                reverse=True,
            )[:10]
            product.purchase_history_html = product._format_history_html(
                purchase_lines, "Sin compras registradas."
            )
            product.sale_history_html = product._format_history_html(
                sale_lines, "Sin ventas registradas."
            )

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
        for vals in vals_list:
            if (
                vals.get("stock_location_id")
                and not vals.get("company_id")
                and self._is_model_available("stock.location")
            ):
                location = self.env["stock.location"].browse(vals["stock_location_id"])
                vals["company_id"] = location.company_id.id or self.env.company.id

            # Limpiar Many2many para evitar comandos inválidos/objetos temporales sin ID
            for many2many_field in ("supplier_taxes_id", "taxes_id"):
                if many2many_field not in vals:
                    continue

                raw_value = vals[many2many_field]
                if not raw_value:
                    vals[many2many_field] = False
                    continue

                valid_ids = []

                if hasattr(raw_value, "ids"):
                    valid_ids.extend([rid for rid in raw_value.ids if isinstance(rid, int) and rid > 0])
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
                                if isinstance(record_id, int) and record_id > 0:
                                    valid_ids.append(record_id)
                        elif command_type == 6:
                            if len(cmd) >= 3 and isinstance(cmd[2], (list, tuple)):
                                for record_id in cmd[2]:
                                    if hasattr(record_id, "id"):
                                        record_id = record_id.id
                                    if isinstance(record_id, int) and record_id > 0:
                                        valid_ids.append(record_id)

                # Mantener SOLO comandos M2M válidos para create: [(6, 0, [ids...])]
                clean_ids = list(dict.fromkeys(valid_ids))
                vals[many2many_field] = [(6, 0, clean_ids)] if clean_ids else False

        products = super().create(vals_list)
        products._sync_pending_pieces()
        products._apply_piece_total_price()
        products._sync_pending_serial_numbers()
        return products

    def write(self, vals):
        if (
            vals.get("stock_location_id")
            and not vals.get("company_id")
            and self._is_model_available("stock.location")
        ):
            location = self.env["stock.location"].browse(vals["stock_location_id"])
            vals["company_id"] = location.company_id.id or self.env.company.id
        result = super().write(vals)
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

    @staticmethod
    def _empty_history_html(message):
        return f"<p class='text-muted mb-0'>{escape(message)}</p>"
