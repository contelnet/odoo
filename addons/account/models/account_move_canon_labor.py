# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    canon_total_ote = fields.Monetary(string='Canon OTE', compute='_compute_canon_labor_totals', currency_field='currency_id', store=False)
    labor_total_ote = fields.Monetary(string='Mano de Obra OTE', compute='_compute_canon_labor_totals', currency_field='currency_id', store=False)
    canon_total = fields.Monetary(string='Canon', compute='_compute_canon_labor_totals', currency_field='currency_id', store=False)
    labor_total = fields.Monetary(string='Mano de Obra', compute='_compute_canon_labor_totals', currency_field='currency_id', store=False)

    @api.depends('invoice_line_ids.price_total', 'invoice_line_ids.product_id')
    def _compute_canon_labor_totals(self):
        for move in self:
            canon_ote = 0.0
            labor_ote = 0.0
            canon = 0.0
            labor = 0.0
            for line in move.invoice_line_ids:
                # Personaliza aquí la lógica según tus productos/campos
                if getattr(line.product_id, 'is_canon', False):
                    canon_ote += line.price_total
                    canon += line.price_total
                elif getattr(line.product_id, 'is_labor', False):
                    labor_ote += line.price_total
                    labor += line.price_total
            move.canon_total_ote = canon_ote
            move.labor_total_ote = labor_ote
            move.canon_total = canon
            move.labor_total = labor
