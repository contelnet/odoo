# --- SCRIPT IMPORTACIÓN ODOO SOLO accounts.csv y contacts.csv ---
import pandas as pd
import xmlrpc.client

# Configuración de conexión Odoo
url = 'https://odoo.contelnet.com'
bd = 'prodOdoo'
usuario = 'plopez@contelnet.com'
password = 'Plr10102002**'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(bd, usuario, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Cargar solo los archivos proporcionados
cuentas = pd.read_csv('accounts.csv').fillna('')
contactos = pd.read_csv('contacts.csv').fillna('')

# Crear empresas (is_company=True) y mapear accountid -> partner_id
accountid2partnerid = {}
for _, row in cuentas.iterrows():
    vals = {
        'name': row['name'],
        'is_company': True,
        'company_type': 'company',
        'type': 'contact',
        'vat': row.get('new_cif', ''),
        'email': row.get('emailaddress1', ''),
        'phone': row.get('address1_telephone1', ''),
        'mobile': row.get('telephone1', ''),
        'website': row.get('websiteurl', ''),
        'street': row.get('address1_line1', ''),
        'city': row.get('address1_city', ''),
        'zip': row.get('address1_postalcode', ''),
        'comment': row.get('description', ''),
        # Contratos/mantenimientos y campos personalizados según res_partner.py
        'contract_office365': str(row.get('contel_office365', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_antivirus': str(row.get('contel_antivirus', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_acronis': str(row.get('contel_acronis', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_vpn': str(row.get('contel_mantenimientovpn', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_cloud_centralita': str(row.get('contel_mantenimientocentralitacloud', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_physical_centralita': str(row.get('contel_mantenimientocentralitafisica', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_total_it_maintenance': str(row.get('contel_mantenimientototalinformatica', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
        'contract_it_bonus': str(row.get('contel_bonoinformatica', '')).strip().lower() in ['true', '1', 'si', 'sí', 'x'],
    }
    partner_id = models.execute_kw(bd, uid, password, 'res.partner', 'create', [vals])
    accountid2partnerid[row['accountid']] = partner_id

# Crear contactos y vincularlos a la empresa usando contel_cuenta
for _, row in contactos.iterrows():
    vals = {
        'name': row['fullname'] if row.get('fullname') else (row.get('firstname', '') + ' ' + row.get('lastname', '')),
        'is_company': False,
        'company_type': 'person',
        'type': 'contact',
        'email': row.get('emailaddress1', ''),
        'phone': row.get('telephone1', ''),
        'mobile': row.get('mobilephone', ''),
        'function': row.get('jobtitle', ''),
        'street': row.get('address1_line1', ''),
        'city': row.get('address1_city', ''),
        'zip': row.get('address1_postalcode', ''),
    }
    # Vincular con empresa usando contel_cuenta
    parent_id = None
    cuenta_id = row.get('contel_cuenta', '').strip()
    if cuenta_id and cuenta_id in accountid2partnerid:
        parent_id = accountid2partnerid[cuenta_id]
    if parent_id:
        vals['parent_id'] = parent_id
    models.execute_kw(bd, uid, password, 'res.partner', 'create', [vals])

print('¡Importación completada! Revisa Odoo para ver los datos.')
