# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestProductCatalogUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country = cls.env.company.account_fiscal_country_id or cls.env.ref('base.es')
        cls.vendor = cls.env['res.partner'].create({
            'name': 'UI Tour Vendor Persist',
            'is_company': True,
        })
        cls.sale_tax = cls.env['account.tax'].create({
            'name': 'UI Tour Sale Tax Persist',
            'amount_type': 'percent',
            'amount': 17.0,
            'type_tax_use': 'sale',
            'country_id': country.id,
            'company_id': cls.env.company.id,
        })
        cls.purchase_tax = cls.env['account.tax'].create({
            'name': 'UI Tour Purchase Tax Persist',
            'amount_type': 'percent',
            'amount': 19.0,
            'type_tax_use': 'purchase',
            'country_id': country.id,
            'company_id': cls.env.company.id,
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Producto UI Tour Persistencia',
            'company_id': cls.env.company.id,
        })

    def test_product_catalog_vendor_tax_persistence_tour(self):
        self.start_tour(
            f"/odoo/action-product.product_template_action_catalog/{self.product.id}?debug=tests",
            'product_catalog_vendor_tax_persistence_tour',
            login='admin',
            timeout=180,
        )

        product = self.env['product.template'].browse(self.product.id)
        self.assertEqual(product.supplier_partner_id, self.vendor)
        self.assertIn(self.purchase_tax, product.supplier_taxes_id)
        self.assertIn(self.sale_tax, product.taxes_id)