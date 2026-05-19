/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("product_catalog_vendor_tax_persistence_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Espera a que cargue el formulario del catálogo",
            trigger: ".o_form_view .o_field_widget[name='name']",
        },
        {
            content: "Activa modo edición",
            trigger: "button.o_form_button_edit",
            run: "click",
        },
        {
            content: "Selecciona el proveedor",
            trigger: ".o_form_editable .o_field_many2one[name='supplier_partner_id'] input",
            run: "edit UI Tour Vendor Persist",
        },
        {
            content: "Confirma el proveedor sugerido",
            trigger: ".o_field_widget[name='supplier_partner_id'] .o-autocomplete--dropdown-menu li:contains(UI Tour Vendor Persist)",
            run: "click",
        },
        {
            content: "Busca impuesto de compra",
            trigger: ".o_form_editable .o_field_widget[name='supplier_taxes_id'] input",
            run: "edit UI Tour Purchase Tax Persist",
        },
        {
            content: "Añade impuesto de compra",
            trigger: ".o_field_widget[name='supplier_taxes_id'] .o-autocomplete--dropdown-menu li:contains(UI Tour Purchase Tax Persist)",
            run: "click",
        },
        {
            content: "Busca impuesto de venta",
            trigger: ".o_form_editable .o_field_widget[name='taxes_id'] input",
            run: "edit UI Tour Sale Tax Persist",
        },
        {
            content: "Añade impuesto de venta",
            trigger: ".o_field_widget[name='taxes_id'] .o-autocomplete--dropdown-menu li:contains(UI Tour Sale Tax Persist)",
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            content: "Comprueba proveedor persistido tras guardar",
            trigger: ".o_form_view .o_field_widget[name='supplier_partner_id']:contains(UI Tour Vendor Persist)",
        },
        {
            content: "Comprueba impuesto de compra persistido tras guardar",
            trigger: ".o_form_view .o_field_widget[name='supplier_taxes_id']:contains(UI Tour Purchase Tax Persist)",
        },
        {
            content: "Comprueba impuesto de venta persistido tras guardar",
            trigger: ".o_form_view .o_field_widget[name='taxes_id']:contains(UI Tour Sale Tax Persist)",
        },
    ],
});