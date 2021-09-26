# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models
import hashlib

APPOINTMENT_TYPE = [
    ('default', 'Odoo Default Appointment'),
    ('accounting', 'Accounting Support Package'),
    ('novobi', 'NOVOBI Appointment')
]


class CalendarAppointmentTypeInherit(models.Model):
    _inherit = "calendar.appointment.type"

    ##########
    # FIELDS
    ##########
    zoom_password = fields.Boolean(string='Use Password', help='If True, use a generated password.')
    novobi_appointment_type = fields.Selection(selection=APPOINTMENT_TYPE,
                                               string='Appointment Type Configuration',
                                               default='default',
                                               help=""" [default]: Odoo Default Appointment Type\n
                                                        [accounting]: Accounting Support Package\n
                                                        [novobi]: NOVOBI Appointment"""
                                               )
    draft_count = fields.Integer('# Draft Appointments', compute='_compute_draft_count')
    website_id = fields.Many2one('website', string="Website")
    personal_meeting_path = fields.Char('Personal Meeting Path', related='website_id.domain')
    appointment_type_website_token = fields.Char(string='Website Token', compute='_compute_appointment_type_website_url', store=True)
    appointment_type_website_url = fields.Char('Website Link', compute='_compute_appointment_type_website_url', store=True, 
        help='The global website url of this appointment to allow the customer to book meeting with employee')
    appointment_type_website_title = fields.Char(string='Website Calendar Title', 
        help='The title shown on Calendar website when using the appointment website global url')
    appointment_type_website_question = fields.Char(string='Website Calendar Question', 
        help='The question shown on Calendar website when using the appointment website')

    ##########
    # COMPUTE
    ##########

    @api.depends()
    def _compute_draft_count(self):
        meeting_data = self.env['calendar.event'].with_context(active_test=False).read_group(
            [('appointment_type_id', 'in', self.ids), ('active', '=', False)],
            ['appointment_type_id'], ['appointment_type_id'])
        mapped_data = {m['appointment_type_id'][0]: m['appointment_type_id_count'] for m in meeting_data}
        for appointment_type in self:
            appointment_type.draft_count = mapped_data.get(appointment_type.id, 0)

    @api.depends('website_id', 'novobi_appointment_type')
    def _compute_appointment_type_website_url(self):
        for record in self:
            if record.website_id:
                event_token = hashlib.md5((record.novobi_appointment_type + str(record.id)).encode('utf-8')).hexdigest()
                record.appointment_type_website_token = event_token
                record.appointment_type_website_url = "https://%s/booking/appointment/calendar?event_token=%s" % (record.website_id.domain, event_token)
            else:
                record.appointment_type_website_url = ''
                record.appointment_type_website_token = ''

    ##########
    # HELPER
    ##########


    def get_appointment_name_on_url(self):
        self.ensure_one()
        return ".".join(self.name.lower().split())

    def action_draft_appointments(self):
        self.ensure_one()
        action = self.env.ref('nerp_appointment.action_draft_event').read()[0]
        context = eval(action['context'])
        del context['search_default_open_events']
        context.update({
            'search_default_appointment_type_id': self.id
        })
        action['context'] = context
        return action

    @api.model
    def get_odoo_accounting_appointment(self, website_id):
        appointment_type_id = self.env['calendar.appointment.type'].search(
            [('novobi_appointment_type', '=', APPOINTMENT_TYPE[1][0]),
             ('website_id', '=', website_id)],
            order='create_date desc', limit=1)
        return appointment_type_id

    @api.model
    def get_odoo_novobi_appointment(self, website_id, event_token):
        appointment_type_id = self.env['calendar.appointment.type'].search(
            [('website_id', '=', website_id),
             ('appointment_type_website_token','=',event_token)],
            order='create_date desc', limit=1
        )
        return appointment_type_id

    def check_if_odoo_accounting_appointment(self):
        self.ensure_one()
        return self.novobi_appointment_type == APPOINTMENT_TYPE[1][0]

    def check_if_odoo_novobi_appointment(self):
        self.ensure_one()
        return self.novobi_appointment_type == APPOINTMENT_TYPE[2][0]
