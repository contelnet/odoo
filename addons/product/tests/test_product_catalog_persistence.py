# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import TransactionCase


class TestProductCatalogPersistence(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Proveedor Persistente',
            'is_company': True,
        })
        cls.sale_tax = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', 'in', [False, cls.env.company.id]),
        ], limit=1)
        cls.purchase_tax = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'purchase'),
            ('company_id', 'in', [False, cls.env.company.id]),
        ], limit=1)

    def test_create_keeps_vendor_and_taxes(self):
        product = self.env['product.template'].create({
            'name': 'Producto persistencia create',
            'supplier_partner_id': [self.vendor.id, self.vendor.display_name],
            'taxes_id': [Command.set(self.sale_tax.ids)],
            'supplier_taxes_id': [Command.set(self.purchase_tax.ids)],
        })

        self.assertEqual(product.supplier_partner_id, self.vendor)
        self.assertEqual(product.taxes_id, self.sale_tax)
        self.assertEqual(product.supplier_taxes_id, self.purchase_tax)

    def test_write_keeps_vendor_and_taxes(self):
        product = self.env['product.template'].create({
            'name': 'Producto persistencia write',
        })

        product.write({
            'supplier_partner_id': [self.vendor.id, self.vendor.display_name],
            'taxes_id': [Command.set(self.sale_tax.ids)],
            'supplier_taxes_id': [Command.set(self.purchase_tax.ids)],
        })

        self.assertEqual(product.supplier_partner_id, self.vendor)
        self.assertEqual(product.taxes_id, self.sale_tax)
        self.assertEqual(product.supplier_taxes_id, self.purchase_tax)
