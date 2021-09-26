# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import http, _, fields
from dateutil.relativedelta import relativedelta
import pytz
import requests as rq
from datetime import datetime
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf
from babel.dates import format_datetime, format_date
import json
from werkzeug.urls import url_encode
import logging
from odoo.osv import expression
from werkzeug.utils import redirect

from odoo.addons.nerp_recaptcha.services.recaptcha.google_recaptcha import ReCaptchaService
from odoo.addons.nerp_appointment.controllers.services_online_booking import WebsiteCalendar


_logger = logging.getLogger(__name__)

class WebsiteCalendar(WebsiteCalendar):

    ##################################
    # PERSONAL APPOINTMENT
    ##################################
    @http.route([
        '/booking/appointment/calendar',
    ],
        type='http', auth="public", website=True)
    def booking_appointment_calendar(self, employee=None, access_token=None, reschedule=False, **kwargs):
        self._clean_session_key('access_token')
        website_id = request.website.id

        template = 'nerp_appointment.schedule_novobi_appointment'
        action = "/booking/appointment/confirm_booking"
        partner_data = {}
        if not reschedule:
            # Here is to check whether the current user is a public user or not
            if not request.env.user._is_public():
                partner_id = request.env.user.partner_id
                partner_data = partner_id.read(
                    fields=['name', 'phone', 'country_id', 'email', 'commercial_company_name'])[0]
                if partner_data.get('name', False):
                    name = partner_data.get('name').split()
                    if len(name) > 1:
                        partner_data['fname'] = name[0]
                        partner_data['lname'] = name[-1]
                    elif len(name) == 1:
                        partner_data['fname'] = name[0]
            # TODO: need to check if the employee is assigned to the appointment
            event_token = kwargs.get('event_token', '')
            appointment_type_id = request.env['calendar.appointment.type'].get_odoo_novobi_appointment(website_id, event_token)

            if not appointment_type_id:
                return request.render('nerp_appointment.novobi_appointment_not_found')
            employee_id = request.env['hr.employee']
            if employee:
                employee_id = request.env['hr.employee'].sudo().search(
                    [('work_email', '=ilike', employee + '@novobi.com')], limit=1)
                if not employee_id:
                    return request.render('nerp_appointment.novobi_appointment_not_found')

            timezone = appointment_type_id.appointment_tz

            # This is where odoo calculate the calendar to show
            slot_ids = appointment_type_id.sudo()._get_appointment_slots(timezone, employee_id)
            return request.render(template, {
                "action": action,
                'appointment_type': appointment_type_id,
                'timezone': timezone,
                'duration': appointment_type_id.appointment_duration,
                'slots': slot_ids,
                "partner_data": partner_data,
                "message": kwargs.get('message') or '',
                'employee': employee,
                'employee_id': employee_id.id,
                'employee_name': employee_id.name,
                'event_token': event_token,
                'reschedule': False
            })
        else:
            event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search([('appointment_type_id', '!=', False),
                                                                    ('access_token', '=', access_token)], limit=1)
            if not event_id or not event_id.sudo().access_token:
                return request.render('nerp_appointment.novobi_appointment_not_found')
                
            if not event_id.active or fields.Datetime.from_string(
                    event_id.allday and event_id.start or event_id.start_datetime) < datetime.now() + relativedelta(
                hours=event_id.appointment_type_id.min_cancellation_hours):
                url = '/booking/appointment/view/%s' % event_id.access_token
                return request.redirect(url)

            employee_id = event_id.employee_id
            employee = employee_id.work_email.split('@')[0]
            timezone = event_id.appointment_type_id.appointment_tz
            slot_ids = event_id.appointment_type_id.sudo()._get_appointment_slots(timezone,
                                                                                  event_id.employee_id)
            # Novobi convention: the 2nd partner is the one that book this meeting
            customer_id = event_id.customer_id
            if not customer_id and len(event_id.partner_ids) > 1:
                customer_id = event_id.partner_ids[1]
            partner_data = customer_id.read(
                fields=['name', 'phone', 'country_id', 'email', 'commercial_company_name'])[0]
            partner_data = self._split_partner_name(partner_data)
            # Convert selected session to appointment timezone
            timezone = event_id.appointment_type_id.appointment_tz
            tz_session = pytz.timezone(timezone)
            start_datetime_str = fields.Datetime.from_string(event_id.start_datetime).replace(
                tzinfo=pytz.utc).astimezone(
                tz_session).strftime('%Y-%m-%d %H:%M:%S')
            return request.render(template, {
                'start_datetime_str': start_datetime_str,
                "action": action,
                'appointment_type': event_id.appointment_type_id,
                'timezone': timezone,
                'duration': event_id.appointment_type_id.appointment_duration,
                'slots': slot_ids,
                "partner_data": partner_data,
                "message": kwargs.get('message') or '',
                'employee': employee,
                'employee_id': employee_id.id,
                'reschedule': True,
                'access_token': access_token
            })

    @http.route([
        '/booking/appointment/confirm_booking',
    ],
        type='http', auth="public", method=['POST'], website=True)
    def booking_appointment_confirmation(self, **kwargs):
        IR_Config = request.env['ir.config_parameter'].sudo()
        employee = kwargs.get('employee', '')
        event_token = kwargs.get('event_token', '')
        website_id = request.website.id
        appointment_type_id = request.env['calendar.appointment.type'].get_odoo_novobi_appointment(website_id, event_token)

        if not appointment_type_id:
            return request.render('nerp_appointment.novobi_appointment_not_found')

        if IR_Config.get_param('recaptchav3') and kwargs.get('recaptcha', False):
            ReCaptchaObject = ReCaptchaService()
            response = ReCaptchaObject.verify_capcha(kwargs)
            _logger.info("Verifing Google reCaptcha on Online Scheduling form...")
            _logger.info(str(response) or 'Something wrong happened')
            if not (response.get('success')
                    and response.get('score') >= float(IR_Config.get_param('recaptchav3._threshold'))
                    and response.get('action') == 'submit_form'):
                if response.get('recaptcha_disabled'):
                    pass
                else:
                    url = '/booking/appointment/calendar?message=robot'
                    if employee:
                        url = '/booking/appointment/calendar?employee=' + employee + '&message=robot'
                    return request.redirect(url)

        datetime_str = kwargs.get('datetime_str', '')
        employee_id = kwargs.get('employee_id', 0)
        employee_id = request.env['hr.employee'].sudo().browse(int(employee_id))
        access_token = kwargs.get('access_token', False) or request.session.get('access_token', False) or ''
        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        if not datetime_str or not employee_id:
            return request.render('nerp_appointment.novobi_appointment_not_found')
        if not event_id:
            event_id = self._create_draft_event(appointment_type_id, kwargs, employee_id)

        date_start, date_end, return_vals = self._recalendar_verify_availability(event_id, datetime_str, employee_id)

        # If the time slot was booked by another customer at the same time
        if not return_vals.get('success', False):
            return_url = '/booking/appointment/calendar?message=%s' % (return_vals.get('message',''))
            if employee:
                return_url = '/booking/appointment/calendar?employee=%s&message=%s' % (employee, return_vals.get('message',''))
            return request.redirect(return_url)

        is_personal_meeting = False
        if employee:
            is_personal_meeting = True
        event_id.sudo().write({
            'start': date_start.strftime(dtf),
            'start_date': date_start.strftime(dtf),
            'start_datetime': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'stop_datetime': date_end.strftime(dtf),
            'partner_ids': [(4, employee_id.user_id.partner_id.id, False)],
            'event_holder': employee_id.id,
            'is_personal_meeting': is_personal_meeting
        })
        event_id.sudo().create_attendees()
        return_url = '/booking/appointment/view/%s?message=new' % event_id.access_token

        return request.redirect(return_url)

    ##################################
    # AFTER BOOKING
    ##################################

    @http.route([
        '/booking/appointment/view/<string:access_token>'
    ],
        type='http', auth="public", website=True)
    def booking_appointment_view(self, access_token, message=False, **kwargs):
        self._clean_session_key('access_token')
        self._clean_session_key('so_id')
        self._clean_session_key('appointment_success_url')
        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        # If can not find event, or event was cancelled (archive but state is open)
        if not event_id or not event_id.sudo().access_token:
            return request.render('nerp_appointment.novobi_appointment_not_found')

        if not event_id.active and event_id.state == 'draft':
            event_id.activate_draft_appointment()

        timezone = event_id.appointment_type_id.appointment_tz
        tz_session = pytz.timezone(timezone)

        if not event_id.allday:
            url_date_start = fields.Datetime.from_string(event_id.start_datetime).strftime('%Y%m%dT%H%M%SZ')
            url_date_stop = fields.Datetime.from_string(event_id.stop_datetime).strftime('%Y%m%dT%H%M%SZ')
            date_start = fields.Datetime.from_string(event_id.start_datetime).replace(tzinfo=pytz.utc).astimezone(
                tz_session)
            date_end = fields.Datetime.from_string(event_id.stop_datetime).replace(tzinfo=pytz.utc).astimezone(
                tz_session)
            date_start = date_start.strftime("%m/%d/%Y %I:%M %p")
            # Novobi convention: appointment start and end in the same date
            date_end = date_end.strftime("%I:%M %p %Z")
            appointment_datetime = date_start + " - " + date_end
        else:
            url_date_start = url_date_stop = fields.Date.from_string(event_id.start_date).strftime('%Y%m%d')
            date_start = fields.Date.from_string(event_id.start_date)
            format_func = format_date
            date_start_suffix = _(', All Day')
            locale = request.env.context.get('lang', 'en_US')
            day_name = format_func(date_start, 'EEE', locale=locale)
            date_start = day_name + ' ' + format_func(date_start, locale=locale) + date_start_suffix

        google_url = ''
        event_query = "event_token=%s" % (event_id.appointment_type_id.appointment_type_website_token)
        if event_id.is_personal_meeting and event_id.employee_id:
            event_query += '&employee=%s' % (event_id.employee_id.work_email.split('@')[0])
        if event_id.active == True:
            zoom_meeting_invitation = event_id.get_zoom_meeting_invitation(event_id.zoom_id)
            details = event_id.appointment_type_id and (
                    event_id.description + '\n' + zoom_meeting_invitation.get('invitation', '')) or ''
            # TODO: upgrade to newer google API
            # This is an really old API of google calendar
            # Ref: https://stackoverflow.com/questions/22757908/google-calendar-render-action-template-parameter-documentation
            # Ref: https://web.archive.org/web/20120313011336/http://www.google.com/googlecalendar/event_publisher_guide.html
            # Ref: https://web.archive.org/web/20120225150257/http://www.google.com/googlecalendar/event_publisher_guide_detail.html
            params_dict = {
                'action': 'TEMPLATE',
                'text': event_id.name,
                'dates': url_date_start + '/' + url_date_stop,
                'details': details,
                'location': event_id.zoom_join_url,
            }
            params = url_encode(params_dict)
            # Add guest list
            params = params + '&add=' + '&add='.join(event_id.partner_ids.mapped('email'))
            google_url = 'https://www.google.com/calendar/render?' + params
        template = 'nerp_appointment.novobi_appointment_summary'

        no_active = False
        if not event_id.active:
            no_active = True

        return request.render(template, {
            'event': event_id,
            'appointment_datetime': appointment_datetime,
            'datetime_start': date_start,
            'google_url': google_url,
            'message': message,
            'timezone': timezone,
            'event_query': event_query,
            'no_active': no_active,
        })

    @http.route([
        '/booking/appointment/reschedule'
    ],
        type='json', auth="public", website=True)
    def booking_appointment_reschedule(self, **kwargs):
        return_vals = {'success': False, 'url': '', 'message': 'Something wrong happen to the system!'}
        access_token = kwargs.get('access_token', '')
        datetime_str = kwargs.get('datetime_str', '')
        employee_id = kwargs.get('employee_id', 0)
        employee_id = request.env['hr.employee'].sudo().browse(int(employee_id))
        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        if not event_id or not datetime_str:
            return_vals = {'success': False, 'url': '', 'message': 'Can not get this meeting in system!'}
            return return_vals

        date_start, date_end, return_vals = self._recalendar_verify_availability(event_id, datetime_str, employee_id)
        if not return_vals.get('success', False):
            return return_vals

        url = '/booking/appointment/view/' + event_id.access_token + '?message=reschedule'
        return_vals.update({
            'url': url
        })

        event_id.reschedule_appointment(datetime_str)
        return return_vals

    @http.route([
        '/booking/appointment/cancel'
    ],
        type='http', auth="public", website=True, method=["POST"])
    def booking_appointment_cancel(self, access_token, **kwargs):
        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)
        url_path = request.httprequest.path
        if not event_id:
            return request.render('nerp_appointment.novobi_appointment_not_found')

        if fields.Datetime.from_string(
                event_id.allday and event_id.start or event_id.start_datetime) < datetime.now() + relativedelta(
            hours=event_id.appointment_type_id.min_cancellation_hours):
            url = '/booking/appointment/view/%s?message=no-cancel' % event_id.access_token
            return request.redirect(url)

        event_id.attendee_ids._send_mail_to_attendees(
            'nerp_appointment.novobi_calendar_template_meeting_cancel',
            force_send=False)
        redirect_url = '/booking/appointment/view/' + access_token + '?message=cancel'

        event_id.write({
            'active': False,
            'state': 'closed'
        })
        event_id.delete_zoom_meeting_room(event_id.zoom_id)
        return request.redirect(redirect_url)

    @http.route(['/booking/appointment/ics/<string:access_token>.ics'], type='http', auth="public", website=True)
    def booking_appointment_ics(self, access_token, **kwargs):
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event or not event.attendee_ids:
            return request.not_found()
        files = event._get_ics_file()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', 'attachment; filename="Online Booking.ics"')
        ])
