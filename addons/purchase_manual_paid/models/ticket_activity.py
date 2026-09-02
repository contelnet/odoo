from odoo import models, fields, api

class HelpdeskTicketCustomActivity(models.Model):
    _name = 'helpdesk.ticket.custom.activity'
    _description = 'Actividades personalizadas del Caso'
    _order = 'date_deadline asc, id desc'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Caso', required=True, ondelete='cascade')
    
    activity_type = fields.Selection([
        ('meeting', 'Cita'),
        ('email', 'Correo electrónico'),
        ('phone', 'Llamada de teléfono'),
        ('task', 'Tarea')
    ], string='Tipo de Actividad', required=True, default='task')
    
    name = fields.Char(string='Descripción / Resumen', required=True)
    user_id = fields.Many2one('res.users', string='Asignado a', default=lambda self: self.env.user)
    date_deadline = fields.Datetime(string='Fecha y hora límite', required=True)
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('done', 'Hecho')
    ], string='Estado', default='pending')

    mail_activity_id = fields.Many2one('mail.activity', string='Actividad Nativa', ondelete='set null')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            activity_type_id = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if rec.activity_type == 'email':
                activity_type_id = self.env.ref('mail.mail_activity_data_email', raise_if_not_found=False)
            elif rec.activity_type == 'phone':
                activity_type_id = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
            
            if activity_type_id:
                deadline_date = rec.date_deadline.date() if rec.date_deadline else False
                activity = rec.ticket_id.activity_schedule(
                    activity_type_id=activity_type_id.id,
                    summary=rec.name,
                    date_deadline=deadline_date,
                    user_id=rec.user_id.id
                )
                rec.mail_activity_id = activity.id
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_vals = {}
        if 'name' in vals:
            sync_vals['summary'] = vals['name']
        if 'date_deadline' in vals:
            if vals['date_deadline']:
                dt = fields.Datetime.to_datetime(vals['date_deadline'])
                sync_vals['date_deadline'] = dt.date()
            else:
                sync_vals['date_deadline'] = False
        if 'user_id' in vals:
            sync_vals['user_id'] = vals['user_id']
            
        if sync_vals:
            for rec in self:
                # Solo sincronizamos si la actividad sigue pendiente para no reabrir fantasmas
                if rec.mail_activity_id and rec.state == 'pending':
                    rec.mail_activity_id.write(sync_vals)
        return res

    def action_mark_done(self):
        for rec in self:
            # 1. Cambiamos el estado en tu tabla local a 'done' (esto hace que se quede en la tabla en verde)
            rec.state = 'done'
            
            # 2. En lugar de borrar la nativa, ejecutamos su acción de marcado como Hecho oficial
            if rec.mail_activity_id:
                try:
                    # action_done() en Odoo marca la actividad como completada y la mueve al historial
                    rec.mail_activity_id.action_done()
                except Exception:
                    pass

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    custom_activity_ids = fields.One2many(
        'helpdesk.ticket.custom.activity',
        'ticket_id',
        string='Actividades'
    )