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
        cls.vendor_2 = cls.env['res.partner'].create({
            'name': 'Proveedor Secundario',
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

    def test_write_keeps_vendor_and_taxes_with_string_and_dict_payloads(self):
        product = self.env['product.template'].create({
            'name': 'Producto persistencia payload web',
        })

        values = {
            'supplier_partner_id': {'resId': self.vendor.id, 'display_name': self.vendor.display_name},
        }
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            values.update({
                'taxes_id': [{'operation': 'SET', 'ids': [str(self.sale_tax.id)]}],
                'supplier_taxes_id': [{'operation': 'SET', 'ids': [str(self.purchase_tax.id)]}],
            })

        product.write(values)

        self.assertEqual(product.supplier_partner_id, self.vendor)
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            self.assertEqual(product.taxes_id, self.sale_tax)
            self.assertEqual(product.supplier_taxes_id, self.purchase_tax)

    def test_write_keeps_vendor_and_taxes_with_nested_relational_payloads(self):
        product = self.env['product.template'].create({
            'name': 'Producto payload relacional anidado',
        })

        values = {
            'supplier_partner_id': [{'id': self.vendor.id, 'display_name': self.vendor.display_name}],
        }
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            values.update({
                'taxes_id': [[self.sale_tax.id, self.sale_tax.display_name]],
                'supplier_taxes_id': [[self.purchase_tax.id, self.purchase_tax.display_name]],
            })

        product.write(values)

        self.assertEqual(product.supplier_partner_id, self.vendor)
        if self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax':
            self.assertEqual(product.taxes_id, self.sale_tax)
            self.assertEqual(product.supplier_taxes_id, self.purchase_tax)

    def test_write_filters_wrong_tax_type_payloads(self):
        product = self.env['product.template'].create({
            'name': 'Producto filtros impuestos',
        })

        if not (self.sale_tax and self.purchase_tax and getattr(self.sale_tax, '_name', '') == 'account.tax'):
            self.skipTest('account.tax no disponible en este entorno de prueba')

        product.write({
            'supplier_taxes_id': [Command.set(self.sale_tax.ids)],
            'taxes_id': [Command.set(self.purchase_tax.ids)],
        })

        self.assertFalse(product.supplier_taxes_id)
        self.assertFalse(product.taxes_id)

    def test_write_creates_serial_numbers_and_keeps_tracking(self):
        product = self.env['product.template'].create({
            'name': 'Producto persistencia seriales',
        })

        product.write({
            'has_serial_number': True,
            'serial_number_input': 'SER-001\nSER-002',
        })

        if 'tracking' in product._fields:
            self.assertEqual(product.tracking, 'serial')
        self.assertTrue(product.has_serial_number)
        self.assertEqual(product.serial_number_ids.mapped('name'), ['SER-001', 'SER-002'])

    def test_quick_vendor_syncs_standard_seller_ids(self):
        product = self.env['product.template'].create({
            'name': 'Producto con proveedor sincronizado',
            'supplier_partner_id': self.vendor.id,
            'supplier_reference': 'REF-PROV-001',
            'standard_price': 99.5,
        })

        quick_seller = product.seller_ids.filtered('is_catalog_quick_supplier')
        self.assertEqual(len(quick_seller), 1)
        self.assertEqual(quick_seller.partner_id, self.vendor)
        self.assertEqual(quick_seller.product_code, 'REF-PROV-001')
        self.assertEqual(quick_seller.price, 99.5)

        product.write({
            'supplier_partner_id': self.vendor_2.id,
            'supplier_reference': 'REF-PROV-002',
            'standard_price': 123.0,
        })

        quick_seller = product.seller_ids.filtered('is_catalog_quick_supplier')
        self.assertEqual(len(quick_seller), 1)
        self.assertEqual(quick_seller.partner_id, self.vendor_2)
        self.assertEqual(quick_seller.product_code, 'REF-PROV-002')
        self.assertEqual(quick_seller.price, 123.0)

