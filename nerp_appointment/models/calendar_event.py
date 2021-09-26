# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.addons.nerp_appointment.services.zoom.zoom_services import ZoomServices
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf
from datetime import datetime
from odoo.exceptions import UserError
import random
import string
from odoo import tools
import pytz
from dateutil.relativedelta import relativedelta
import json
import logging


class CalendarEventInherit(models.Model):
    _inherit = "calendar.event"

    _services = {}

    ##########
    # FIELDS
    ##########

    employee_id = fields.Many2one('hr.employee',
                                  help='Check if this appointment is personal online appointment booked via Employee URL')
    event_holder = fields.Many2one('hr.employee', help='Initial employee assigned to this appointment via website')
    customer_id = fields.Many2one('res.partner', help='The customer that booked this meeting')
    zoom_id = fields.Char(string='Zoom Room ID')
    zoom_start_url = fields.Char(string='Start Zoom URL')
    zoom_join_url = fields.Char(string='Join Zoom URL')
    zoom_password = fields.Char(string='Zoom Meeting Password', help='Password of Zoom meeting room.')
    stage_id = fields.Many2one('calendar.event.stage', compute='_compute_stage_id', search='_search_stage_id',
                               default=lambda self: self.env.ref('nerp_appointment.draft_stage'))
    novobi_state = fields.Selection(related='stage_id.state')
    selected_topics = fields.Char(help='Dictionary of topics for online appointment')
    state = fields.Selection(selection_add=[('closed', 'Closed')])
    so_id = fields.Many2one('sale.order',
                            help='If this appointment an Odoo Accounting appointment, then this field is required')
    company_id = fields.Many2one('res.company', string='Company',
                                 help='Customzed fields, linked to company which creates this event')
    is_personal_meeting = fields.Boolean(string='Is Personal Meeting', help='If the meeting is booked from the personal url or from the event global url.')

    ##########
    # GENERAL
    ##########

    @api.model
    def create(self, vals):
        res = super(CalendarEventInherit, self).create(vals)
        if res.appointment_type_id:
            appointment_type_id = res.appointment_type_id
            if appointment_type_id.novobi_appointment_type == 'default':
                pass
            else:
                if appointment_type_id.zoom_password:
                    zoom_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(8))
                    res.zoom_password = zoom_password
        return res

    def write(self, vals):
        res = super(CalendarEventInherit, self).write(vals)
        for record in self:
            if record.zoom_id:
                if vals.get('duration', False) or vals.get('start_datetime', False) or vals.get('zoom_password', False):
                    record.update_zoom_meeting_room(record.zoom_id)
        return res

    def unlink(self, can_be_deleted=False):
        for record in self:
            if record.zoom_id:
                record.delete_zoom_meeting_room(record.zoom_id)
        return super(CalendarEventInherit, self).unlink()

    def unlink(self, can_be_deleted=False):
        return super(CalendarEventInherit, self).unlink()

    ##########
    # COMPUTE
    ##########

    @api.depends('active', 'start_datetime', 'start_date', 'start')
    def _compute_stage_id(self):
        # TODO: optimize the below code
        for record in list(set(self.search([]) + self)):
            try:
                if not record.active:
                    record.stage_id = self.env.ref('nerp_appointment.draft_stage')
                else:
                    if record.recurrency:
                        if record.allday:
                            if fields.Datetime.from_string(record.start_date).date() >= datetime.utcnow().date():
                                record.stage_id = self.env.ref('nerp_appointment.open_stage')
                            else:
                                if type(record.id) is str:
                                    detach_event = record.detach_recurring_event()
                                    detach_event.stage_id = self.env.ref('nerp_appointment.closed_stage')
                                else:
                                    record.stage_id = self.env.ref('nerp_appointment.closed_stage')
                        else:
                            if fields.Datetime.from_string(record.start_datetime) >= datetime.utcnow():
                                record.stage_id = self.env.ref('nerp_appointment.open_stage')
                            else:
                                if type(record.id) is str:
                                    detach_event = record.detach_recurring_event()
                                    detach_event.stage_id = self.env.ref('nerp_appointment.closed_stage')
                                else:
                                    record.stage_id = self.env.ref('nerp_appointment.closed_stage')
                    else:
                        if not record.allday and record.start_datetime >= datetime.utcnow():
                            record.stage_id = self.env.ref('nerp_appointment.open_stage')
                        elif record.allday and record.start_date >= datetime.utcnow().date():
                            record.stage_id = self.env.ref('nerp_appointment.open_stage')
                        else:
                            record.stage_id = self.env.ref('nerp_appointment.closed_stage')
            except TypeError:
                pass

    ##########
    # SEARCH
    ##########

    def _search_stage_id(self, operator, value):
        if operator != '=':
            if value == 'draft':
                return [('active', '=', False)]
            elif value == 'open':
                return [('start_datetime', '>=', datetime.utcnow())]
            elif value == 'closed':
                return [('start_datetime', '<', datetime.utcnow())]

    ##########
    # HELPER
    ##########

    def get_select_topics(self):
        topics = json.loads(self.selected_topics)
        topics_list = []
        if topics.get('default', False):
            topics_list += topics['default']
        if topics.get('other', False):
            topics_list += topics['other']
        return topics_list

    def get_time_interval(self, tz):
        """
         Format and localize date time to be used in email templates.
         This function specialize in using AM and PM format for datetime
        :param time_interval:
        :param string tz: Timezone indicator (optional)
        :return:
        """
        self.ensure_one()
        date = fields.Datetime.from_string(self.start)
        timezone = pytz.timezone(tz or 'UTC')
        date = date.replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
        result = tools.ustr(date.strftime("%I:%M %p %Z"))

        return result

    def send_invitation_email_to_attendees(self):
        for record in self:
            if record.attendee_ids and record.partner_ids:
                # The below line of code block emails sent to current logged in user
                # to_notify = record.attendee_ids.filtered(lambda a: a.email != self.env.user.email)
                # Change user for creating emails
                to_notify = record.attendee_ids
                to_notify._send_mail_to_attendees('calendar.calendar_template_meeting_invitation',
                                                               force_send=False)

    @api.model
    def get_service(self, service_name):
        # if not self._services.get(service_name, False):
        if service_name == 'zoom':
            IR_Config = self.env['ir.config_parameter'].sudo()
            if self.appointment_type_id.check_if_odoo_novobi_appointment():
                if self.event_holder.zoom_api_key and self.event_holder.zoom_api_secret and self.event_holder.zoom_email:
                    self._services[service_name] = ZoomServices(zoom_api_key=self.event_holder.zoom_api_key,
                                                                zoom_api_secret=self.event_holder.zoom_api_secret,
                                                                zoom_email=self.event_holder.zoom_email)
                else:
                    self._services[service_name] = ZoomServices(zoom_api_key=IR_Config.get_param('zoom._api_key'),
                                                                zoom_api_secret=IR_Config.get_param('zoom._api_secret'),
                                                                zoom_email=IR_Config.get_param('zoom._email'))
            else:
                self._services[service_name] = ZoomServices(zoom_api_key=IR_Config.get_param('zoom._api_key'),
                                                            zoom_api_secret=IR_Config.get_param('zoom._api_secret'),
                                                            zoom_email=IR_Config.get_param('zoom._email'))
        return self._services[service_name]

    def get_zoom_meeting_invitation(self, zoom_id):
        self.ensure_one()
        if self.zoom_id:
            zoom_service = self.get_service('zoom')
            invitation = zoom_service.get_meeting_invitation(zoom_id)
        else:
            invitation = {'error': 'Zoom meeting is not created'}
        return invitation

    def create_zoom_meeting_room(self):
        self.ensure_one()
        zoom_service = self.get_service('zoom')
        start_time = datetime.strftime(self.start_datetime, '%Y-%m-%dT%H:%M:%SZ')
        room_info = {
            'topic': self.name,
            'start_time': start_time,
            'duration': self.duration * 60,  # Convert from hours in Odoo to minutes in Zoom API
            'timezone': 'UTC',  # Because Odoo stores dattime in UTC timezone
        }
        if self.zoom_password:
            room_info.update({'password': self.zoom_password})
        meeting_info = zoom_service.create_meeting(room_info)
        return meeting_info

    def delete_zoom_meeting_room(self, zoom_id):
        self.ensure_one()
        zoom_service = self.get_service('zoom')
        result = zoom_service.delete_meeting(zoom_id)
        return result

    def update_zoom_meeting_room(self, zoom_id):
        self.ensure_one()
        zoom_service = self.get_service('zoom')
        start_time = datetime.strftime(self.start_datetime, '%Y-%m-%dT%H:%M:%SZ')
        values = {
            'duration': self.duration * 60,
            'start_time': start_time
        }
        if self.zoom_password:
            values.update({'password': self.zoom_password})
        return zoom_service.update_meeting(zoom_id, values)

    def _get_ics_file(self):
        result = super(CalendarEventInherit, self)._get_ics_file()
        # Copy from odoo
        import vobject
        for event in self:
            event_ics = vobject.readOne(result[event.id].decode("utf-8"))
            if event.zoom_join_url:
                event_ics.vevent.location.value = event.zoom_join_url
            zoom_meeting_invitation = event.get_zoom_meeting_invitation(event.zoom_id).get('invitation', '')
            if zoom_meeting_invitation:
                event_ics.vevent.description.value += '\n' + zoom_meeting_invitation
            organizer_add = event_ics.vevent.add('organizer')
            organizer_add.value = u'MAILTO:' + (event.event_holder.user_id.partner_id.email or u'')
            result[event.id] = event_ics.serialize().encode('utf-8')
        return result

    def get_invitation_email_subject(self):
        topics = self.get_select_topics()
        subject = ''
        if len(topics) == 1:
            subject = topics[0]
        elif len(topics) == 0:
            subject = self.customer_id.name + ' and ' + self.event_holder.user_id.partner_id.name
        return subject

    def get_individual_meeting_email_sender(self):
        sender = self.company_id.partner_id
        assigned_employee = self.event_holder.user_id.partner_id
        if assigned_employee:
            sender = assigned_employee
        return sender

    #############################
    # CONTROLLER Services
    #############################
    def activate_draft_appointment(self):
        self.ensure_one()
        event_id = self
        if not event_id.active:
            # Set accept invitation on all attendees
            event_id.sudo().attendee_ids.sudo().write({'state': 'accepted'})
            # Create Zoom meeting room
            meeting_info = event_id.sudo().create_zoom_meeting_room()
            # Change active to True
            event_id.sudo().write({
                'active': True,
                'state': 'open',
                'zoom_id': meeting_info.get('id', ''),
                'zoom_start_url': meeting_info.get('start_url', ''),
                'zoom_join_url': meeting_info.get('join_url', ''),
            })
            # We prevent Odoo from sending invitation to draft event and send emails to all attendees only when the booking is complete.
            # This is because we create draft event right after customer filled in the form.
            event_id.sudo().send_invitation_email_to_attendees()
        return event_id

    def reschedule_appointment(self, datetime_str):
        self.ensure_one()
        event_id = self
        tz_session = pytz.timezone(event_id.appointment_type_id.appointment_tz)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        date_end = date_start + relativedelta(hours=event_id.appointment_type_id.appointment_duration)
        event_id.write({
            'start_date': date_start.strftime(dtf),
            'start_datetime': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'stop_datetime': date_end.strftime(dtf)
        })
        return event_id