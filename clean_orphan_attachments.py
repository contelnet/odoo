# Script para limpiar adjuntos huérfanos en Odoo
# Uso: ./odoo-bin shell -c debian/odoo.conf -d <tu_base_datos> -i <modulo_base>

import os
from odoo import api, SUPERUSER_ID

def clean_orphan_attachments(env):
    Attachment = env['ir.attachment']
    count = 0
    for att in Attachment.search([('store_fname', '!=', False)]):
        try:
            if not os.path.exists(att._full_path(att.store_fname)):
                att.unlink()
                count += 1
        except Exception as e:
            print(f"Error al procesar adjunto {att.id}: {e}")
    print(f"Adjuntos huérfanos eliminados: {count}")

# Ejecutar en entorno Odoo shell
def run_clean():
    env = api.Environment(cr, SUPERUSER_ID, {})
    clean_orphan_attachments(env)

run_clean()
