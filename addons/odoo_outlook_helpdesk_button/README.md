# Outlook Helpdesk Button

Este módulo añade un botón "Crear ticket" al panel de Outlook en Odoo 18, permitiendo abrir el formulario de helpdesk.ticket con el asunto y cuerpo del correo precargados.

## Instalación
1. Copia la carpeta `odoo_outlook_helpdesk_button` en tus addons.
2. Actualiza la lista de apps y busca "Outlook Helpdesk Button".
3. Instala el módulo.

## Notas técnicas
- Parchea el componente OWL `OutlookPanel` de `odoo_outlook`.
- Inyecta el botón en la zona de acciones del panel.
- Usa los assets de `odoo_outlook.assets`.
- Si el botón no aparece, revisa el import y el xpath según tu versión.

## Autor
Contelnet / Pablo