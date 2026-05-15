# Outlook Helpdesk Button

Este módulo añade un botón para crear casos/tickets desde el panel de Outlook en Odoo 18.
Ahora crea el `helpdesk.ticket` directamente en backend a partir del correo actual y después abre el ticket creado en Odoo.

## Instalación
1. Copia la carpeta `odoo_outlook_helpdesk_button` en tus addons.
2. Actualiza la lista de apps y busca "Outlook Helpdesk Button".
3. Instala el módulo.
4. Descarga el complemento desde `Outlook y Odoo` y configúralo con tu servidor y base de datos.

## Notas técnicas
- Parchea el componente OWL `OutlookPanel` de `odoo_outlook`.
- Inyecta el botón en la zona de acciones del panel.
- Usa los assets de `odoo_outlook.assets`.
- Crea el ticket por JSON-RPC en backend y abre el caso ya creado.
- Si la creación automática falla, abre un formulario precargado como respaldo.
- Si el botón no aparece, revisa el import y el xpath según tu versión.

## Autor
Contelnet / Pablo