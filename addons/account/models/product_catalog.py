from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

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
        return

    @api.constrains("supplier_taxes_id", "taxes_id")
    def _check_catalog_taxes_filter(self):
        for product in self:
            if getattr(product.supplier_taxes_id, "_name", None) == "_unknown":
                continue
            if (
                product.supplier_taxes_id
                and "type_tax_use" in product.supplier_taxes_id._fields
                and any(tax.type_tax_use != "purchase" for tax in product.supplier_taxes_id)
            ):
                raise ValidationError(
                    _("Los impuestos de compra solo pueden tener tipo de uso 'purchase'.")
                )
            if getattr(product.taxes_id, "_name", None) == "_unknown":
                continue
            if (
                product.taxes_id
                and "type_tax_use" in product.taxes_id._fields
                and any(tax.type_tax_use != "sale" for tax in product.taxes_id)
            ):
                raise ValidationError(
                    _("Los impuestos de venta solo pueden tener tipo de uso 'sale'.")
                )
