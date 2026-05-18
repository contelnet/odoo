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
        account_tax_model = cls.env.get('account.tax')
        cls.sale_tax = account_tax_model.search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', 'in', [False, cls.env.company.id]),
        ], limit=1) if account_tax_model else cls.env['res.partner']
        cls.purchase_tax = account_tax_model.search([
            ('type_tax_use', '=', 'purchase'),
            ('company_id', 'in', [False, cls.env.company.id]),
        ], limit=1) if account_tax_model else cls.env['res.partner']

    def test_create_keeps_vendor_and_taxes(self):
        values = {
            'name': 'Producto persistencia create',
            'supplier_partner_id': [self.vendor.id, self.vendor.display_name],
        }
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            values.update({
                'taxes_id': [Command.set(self.sale_tax.ids)],
                'supplier_taxes_id': [Command.set(self.purchase_tax.ids)],
            })

        product = self.env['product.template'].create(values)

        self.assertEqual(product.supplier_partner_id, self.vendor)
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            self.assertEqual(product.taxes_id, self.sale_tax)
            self.assertEqual(product.supplier_taxes_id, self.purchase_tax)

    def test_write_keeps_vendor_and_taxes(self):
        product = self.env['product.template'].create({
            'name': 'Producto persistencia write',
        })

        values = {
            'supplier_partner_id': [self.vendor.id, self.vendor.display_name],
        }
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            values.update({
                'taxes_id': [Command.set(self.sale_tax.ids)],
                'supplier_taxes_id': [Command.set(self.purchase_tax.ids)],
            })

        product.write(values)

        self.assertEqual(product.supplier_partner_id, self.vendor)
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            self.assertEqual(product.taxes_id, self.sale_tax)
            self.assertEqual(product.supplier_taxes_id, self.purchase_tax)
