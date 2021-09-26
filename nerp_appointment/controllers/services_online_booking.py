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

from odoo.addons.nerp_recaptcha.services.recaptcha.google_recaptcha import ReCaptchaService

_logger = logging.getLogger(__name__)

class WebsiteCalendar(http.Controller):

    ##################################
    # Services page
    #   Because we have two /services pages for two websites,
    #     so that we have to lookup in database to get the correct view for each website
    #   The parameter may not need on NOVOBI website, but we deal with it to minimize the effort
    #     and make the controller flexible
    ##################################

    @http.route([
        '/services'
    ],
        type='http', auth="public", website=True)
    def novobi_calendar_appointment_info(self, **kwargs):
        website_id = request.website.id
        view_id = self._check_site_restriction(request.httprequest.path)
        if not view_id:
            return request.render('http_routing.404')

        self._clean_session_key('access_token')
        partner_data = {}

        # Here is to check whether the current user is a public user or not, then fill user data to the form
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

        appointment_type_id = request.env['calendar.appointment.type'].get_odoo_accounting_appointment(website_id)
        action = '/services/appointment/calendar'
        return view_id.render(values={
            "partner_data": partner_data,
            "appointment_type": appointment_type_id,
            "action": action,
            "message": kwargs.get('message') or '',
            "packages": self._get_package_list_desc()
        })

    @http.route([
        '/services/appointment/calendar'
    ],
        type='http', auth="public", website=True, method=["POST"])
    def services_appointment_calendar(self, access_token=None, reschedule=False, **kwargs):
        website_id = request.website.id
        appointment_type_id = request.env['calendar.appointment.type'].get_odoo_accounting_appointment(website_id)
        if not appointment_type_id:
            return request.render('nerp_appointment.finance_appointment_not_found')
        template = 'nerp_appointment.schedule_finance_appointment'

        if not reschedule:
            # For some reason, request.redirect return [302 FOUND]
            # TODO: re-test with redirect
            # This is json rpc, normal post method need csrf_token in data param
            IR_Config = request.env['ir.config_parameter'].sudo()

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
                        return request.redirect('/services?message=robot')
            timezone = appointment_type_id.appointment_tz
            
            partner_id = request.env['res.partner'].sudo().get_partner(kwargs)
            if not partner_id:
                return request.render('nerp_appointment.finance_appointment_not_found')

            event_id = self._create_draft_event(appointment_type_id, kwargs)
            # This is where odoo calculate the calendar to show
            slot_ids = appointment_type_id.sudo()._get_appointment_slots(timezone)
            # Allow to render two month only
            if len(slot_ids) >= 3:
                slot_ids = slot_ids[0:2]
            return request.render(template, {
                'access_token': event_id.access_token,
                'appointment_type': appointment_type_id,
                'timezone': timezone,
                'duration': appointment_type_id.appointment_duration,
                'slots': slot_ids,
            })
        else:
            event_id = request.env['calendar.event'].sudo().search([('appointment_type_id', '!=', False),
                                                                    ('access_token', '=', access_token)], limit=1)
            if not event_id:
                return request.render('nerp_appointment.finance_appointment_not_found')

            if fields.Datetime.from_string(
                    event_id.allday and event_id.start or event_id.start_datetime) < datetime.now() + relativedelta(
                hours=event_id.appointment_type_id.min_cancellation_hours):
                url = '/services/appointment/view/%s?message=no-reschedule' % event_id.access_token
                return request.redirect(url)
            timezone = event_id.appointment_type_id.appointment_tz
            slot_ids = event_id.appointment_type_id.sudo()._get_appointment_slots(timezone)
            # Allow to render two month only
            if len(slot_ids) >= 3:
                slot_ids = slot_ids[0:2]
            return request.render(template, {
                'event': event_id,
                'appointment_type': event_id.appointment_type_id,
                'access_token': event_id.access_token,
                'timezone': timezone,
                'duration': appointment_type_id.appointment_duration,
                'slots': slot_ids,
                'reschedule': True,
            })

    @http.route([
        '/services/appointment/check_slot_appointment',
    ],
        type='json', auth="public", website=True)
    def services_appointment_check_slot(self, **kwargs):
        datetime_str = kwargs.get('datetime_str', '')
        employee_id = kwargs.get('employee_id', 0)
        employee_id = request.env['hr.employee'].sudo().browse(int(employee_id))
        access_token = kwargs.get('access_token', '')

        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        if not event_id:
            return_vals = {
                'success': False,
                'message': 'The meeting is no longer available. Please refresh your browser and try again.'
            }
            return return_vals

        request.session['access_token'] = access_token
        date_start, date_end, return_vals = self._recalendar_verify_availability(event_id, datetime_str, employee_id)
        if not return_vals.get('success', False):
            return return_vals

        # Update draft info of the event while keeping active as False to prevent odoo from sending any email
        event_id.sudo().write({
            'start': date_start.strftime(dtf),
            'start_date': date_start.strftime(dtf),
            'start_datetime': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'stop_datetime': date_end.strftime(dtf),
            'partner_ids': [(4, employee_id.user_id.partner_id.id, False)],
            'event_holder': employee_id.id
        })
        event_id.sudo().create_attendees()
        url = '/services/packages'
        request.session['access_token'] = access_token
        return_vals.update({
            'url': url
        })
        return return_vals

    @http.route(['/services/packages'], type='http', auth="public", website=True)
    def services_appointment_packages(self, **kwargs):
        if request.session.get('access_token'):
            packages = self._get_package_list_desc()
            return request.render("nerp_appointment.finance_suppport_session_packages", {
                "packages": packages,
            })
        else:
            return request.render('nerp_appointment.finance_appointment_not_found')

    ##############################################################################
    # @Description
    # - After customer select a package, redirect customer to checkout page
    # - Create a Sale Order and store it in session, to prevent creating duplicated one when customer
    #   click back button on website
    # - Create an url and store it in session to redirect customer when paying successfully
    # @Params
    #   Quantity: quantity of package
    ##############################################################################

    @http.route(['/services/checkout'], type='http', auth="public", website=True)
    def services_appointment_checkout(self, quantity, **kwargs):
        if request.session.get('access_token'):
            access_token = request.session.get('access_token')
            event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
                [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)
            returndata = '/services/appointment/view/%s?message=new' % (access_token)
            request.session['appointment_success_url'] = returndata
            package_id = request.env['service.packages'].sudo().get_support_session_service(quantity,
                                                                                            package_type='finance_appointment')
            so_id = request.env['sale.order'].sudo()
            if not package_id:
                return request.render('nerp_appointment.finance_appointment_not_found')
            product_id = package_id.product_template_id

            # TODO: use SO access token to further business logic
            if not request.session.get('so_id', False):
                res_company = request.website.company_id
                if not res_company:
                    res_company = request.env['res.company'].sudo().search([('name', 'ilike', 'Odoo Accounting')],
                                                                           limit=1)
                so_id = request.env['sale.order'].sudo().create({
                    'partner_id': request.session.get('partner_id'),
                    'payment_term_id': request.env.ref('account.account_payment_term_immediate').id,
                    'company_id': res_company and res_company.id or False,
                    'user_id': False,
                    'team_id': False,
                })
                so_id.write({'state': 'sent'})
                request.env.cr.commit()
                request.session['so_id'] = so_id.id
            else:
                so_id = request.env['sale.order'].sudo().browse(request.session['so_id'])
                if so_id.state == 'draft':
                    so_id.write({'partner_id': request.session.get('partner_id')})
                so_id.write({'state': 'sent'})
            if so_id.order_line:
                so_id.order_line.unlink()
            discount_product_id = request.env.ref('nerp_appointment.nerp_discount_product').sudo()
            so_id.write({'order_line': [
                (0, False, {
                    'product_id': product_id.product_variant_id.id,
                    'name': product_id.name,
                    'product_uom_qty': int(quantity),
                    'price_unit': product_id.list_price,
                }),
                (0, False, {
                    'product_id': discount_product_id.product_variant_id.id,
                    'name': discount_product_id.name,
                    'product_uom_qty': 1,
                    'price_unit': package_id.price - int(quantity) * product_id.list_price,
                })
            ]})

            event_id.sudo().write({
                'so_id': so_id.id,
            })
            event_id.flush()
            values = {
                'sale_order': so_id,
                'partner_id': so_id.partner_id.id,
                'package': self._get_package_desc(package_id),
                'access_token': access_token,
            }

            # The following code is a copy of line 177-187 in addons/sale/controlelrs/portal.py
            if so_id.has_to_be_paid():
                domain = expression.AND([
                    ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', so_id.company_id.id)],
                    ['|', ('country_ids', '=', False), ('country_ids', 'in', [so_id.partner_id.country_id.id])]
                ])
                acquirers = request.env['payment.acquirer'].sudo().search(domain)

                values['acquirers'] = acquirers.filtered(
                    lambda acq: (acq.payment_flow == 'form' and acq.view_template_id) or
                                (acq.payment_flow == 's2s' and acq.registration_view_template_id))
                values['pms'] = request.env['payment.token'].search([('partner_id', '=', so_id.partner_id.id)])
                values['acq_extra_fees'] = acquirers.get_acquirer_extra_fees(so_id.amount_total,
                                                                             so_id.currency_id,
                                                                             so_id.partner_id.country_id.id)

            return request.render('nerp_appointment.finance_suppport_session_checkout', values)

        return request.render('nerp_appointment.finance_appointment_not_found')

    ##################################
    # AFTER BOOKING
    ##################################

    @http.route([
        '/services/appointment/view/<string:access_token>'
    ],
        type='http', auth="public", website=True)
    def services_appointment_view(self, access_token, message=False, **kwargs):
        self._clean_session_key('access_token')
        self._clean_session_key('so_id')
        self._clean_session_key('appointment_success_url')
        event_id = request.env['calendar.event'].sudo().with_context(active_test=False).search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        # I think we only set active the appointment when the payment is complete and this is not a cancelled appointment
        # We will send email and active the event 

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
        employee_query = ""
        if event_id.employee_id:
            employee_query = 'employee=' + event_id.employee_id.work_email.split('@')[0]
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

        template = 'nerp_appointment.finance_appointment_summary'

        return request.render(template, {
            'event': event_id,
            'appointment_datetime': appointment_datetime,
            'datetime_start': date_start,
            'google_url': google_url,
            'message': message,
            'timezone': timezone,
            'employee_query': employee_query
        })

    @http.route([
        '/services/appointment/reschedule'
    ],
        type='json', auth="public", website=True)
    def services_appointment_reschedule(self, **kwargs):
        return_vals = {'success': False, 'url': '', 'message': 'Something wrong happen to the system!'}
        access_token = kwargs.get('access_token', '')
        datetime_str = kwargs.get('datetime_str', '')
        employee_id = kwargs.get('employee_id', 0)
        employee_id = request.env['hr.employee'].sudo().browse(int(employee_id))
        event_id = request.env['calendar.event'].sudo().search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        if not event_id or not datetime_str:
            return_vals = {'success': False, 'url': '', 'message': 'Can not get this meeting in system!'}
            return return_vals

        date_start, date_end, return_vals = self._recalendar_verify_availability(event_id, datetime_str, employee_id)
        if not return_vals.get('success', False):
            return return_vals

        url = '/services/appointment/view/' + event_id.access_token + '?message=reschedule'
        return_vals.update({
            'url': url
        })

        # Write new datetime to the event for rescheduling
        event_id.reschedule_appointment(datetime_str)
        return return_vals

    @http.route([
        '/services/appointment/cancel'
    ],
        type='http', auth="public", website=True, method=["POST"])
    def services_appointment_cancel(self, access_token, **kwargs):
        event_id = request.env['calendar.event'].sudo().search(
            [('appointment_type_id', '!=', False), ('access_token', '=', access_token)], limit=1)

        if not event_id:
            return request.render('nerp_appointment.finance_appointment_not_found')

        if fields.Datetime.from_string(
                event_id.allday and event_id.start or event_id.start_datetime) < datetime.now() + relativedelta(
            hours=event_id.appointment_type_id.min_cancellation_hours):
            url = '/services/appointment/view/%s?message=no-cancel' % event_id.access_token
            return request.redirect(url)

        appointment_type_id = event_id.appointment_type_id
        so_id = event_id.sudo().so_id
        if not so_id or not so_id.transaction_ids:
            return request.render('nerp_appointment.finance_appointment_not_found')
        context = {
            'transaction': so_id.transaction_ids[0],
        }
        event_id.sudo().attendee_ids._send_mail_to_attendees(
            'nerp_appointment.finance_calendar_template_meeting_cancel',
            force_send=False)
        notify_admin_cancel_meeting_template = request.env.ref('nerp_appointment.finance_calendar_template_meeting_cancel_for_admin')
        notify_admin_cancel_meeting_template.sudo().with_context(context).send_mail(so_id.id)
        redirect_url = '/services/appointment/view/' + access_token + '?message=cancel'
        event_id.write({
            'active': False,
            'state': 'closed'
        })
        event_id.delete_zoom_meeting_room(event_id.zoom_id)
        return request.redirect(redirect_url)

    @http.route(['/services/appointment/ics/<string:access_token>.ics'], type='http', auth="public", website=True)
    def services_appointment_ics(self, access_token, **kwargs):
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not event or not event.attendee_ids:
            return request.not_found()
        files = event._get_ics_file()
        content = files[event.id]
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', 'attachment; filename="Odoo Accounting Appointment.ics"')
        ])

    ##########
    # HELPER
    ##########

    def _clean_session_key(self, key):
        if request.session.get(key, False):
            del request.session[key]

    def _create_draft_event(self, appointment_type, kwargs, employee_id=None):
        fname = kwargs.get('fname')
        lname = kwargs.get('lname')
        name = kwargs.get('name', False)
        email = kwargs.get('email')
        phone = kwargs.get('phone')
        partner_id = request.env['res.partner'].sudo().get_partner(kwargs)

        request.session['partner_id'] = partner_id.id
        description = ('Phone: %s\n'
                       'Email: %s\n' % (phone, email))
        selected_topics = {}
        partner_ids = [partner_id]
        # NOTE: This field only has meaning when it come to OmniBorders personal meeting
        subject = kwargs.get('subject', False)
        guests_emails = kwargs.get('guests_emails', False)
        if guests_emails:
            guest_ids = []
            guests_emails = guests_emails.split(',')
            for email in guests_emails:
                guest_id = request.env['res.partner'].sudo().get_partner({'email': email})
                guest_ids += [guest_id]
            partner_ids = list(set(partner_ids + guest_ids))

        if subject:
            selected_topics.update({'other': [subject]})

        for question in appointment_type.question_ids.filtered(lambda q: q.question_type == 'checkbox'):
            key = 'question_' + str(question.id)
            answers = question.answer_ids.filtered(lambda x: (key + '_answer_' + str(x.id)) in kwargs)
            if answers:
                description += question.name + ': \n -' + '\n -'.join(answers.mapped('name')) + '\n'
                selected_topics.update({'default': answers.mapped('name')})
        for question in appointment_type.question_ids.filtered(lambda q: q.question_type == 'text'):
            key = 'question_' + str(question.id)
            if kwargs.get(key):
                description += question.name + ': \n -' + kwargs.get(key) + '\n'
                selected_topics.update({'other': [kwargs.get(key)]})

        categ_id = request.env.ref('website_calendar.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or []

        res_company = request.website.company_id
        # NOTE: what is the point of these code lines ? Company should be pre-config for every website
        # if not res_company:
        #     if appointment_type.check_if_odoo_accounting_appointment():
        #         res_company = request.env['res.company'].sudo().search([('name', 'ilike', 'Novobi')], limit=1)
        #     elif appointment_type.check_if_odoo_novobi_appointment():
        #         res_company = request.env['res.company'].sudo().search([('name', 'ilike', 'Odoo Accounting')], limit=1)

        # Create draft event with start_datetime of created_time
        event = request.env['calendar.event'].sudo().create({
            'state': 'draft',
            'name': _('%s with %s') % (appointment_type.name, name or (fname + ' ' + lname)),
            'start': datetime.now().strftime(dtf),
            'start_date': datetime.now().strftime(dtf),
            'start_datetime': datetime.now().strftime(dtf),
            'stop': datetime.now().strftime(dtf),
            'stop_datetime': datetime.now().strftime(dtf),
            'allday': False,
            'duration': appointment_type.appointment_duration,
            'description': description,
            'selected_topics': json.dumps(selected_topics),
            'alarm_ids': alarm_ids,
            'location': appointment_type.location,
            'categ_ids': [(4, categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'partner_ids': [(4, pid.id, False) for pid in partner_ids],
            'active': False,
            'location': 'Zoom Meeting',
            'company_id': res_company and res_company.id or False,
            'customer_id': partner_id.id,
        })

        # For personal meeting, add employee_id to event for later rescheduling
        if employee_id:
            event.write({
                'employee_id': employee_id.id
            })
        return event

    def _recalendar_verify_availability(self, event_id, datetime_str, employee_id=None):
        return_vals = {'success': True, 'url': '', 'message': ''}
        customer_partner_ids = event_id.partner_ids.filtered(lambda p: p.id not in [employee_id.user_id.partner_id.id])

        timezone = event_id.appointment_type_id.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        date_end = date_start + relativedelta(hours=event_id.appointment_type_id.appointment_duration)

        if employee_id.user_id and employee_id.user_id.partner_id:
            if not employee_id.user_id.partner_id.with_context(active_test=True).calendar_verify_availability(
                    date_start, date_end):
                return_vals.update({
                    'success': False,
                    'message': 'The selected time slot is no longer available.'
                })
                return date_start, date_end, return_vals

        for partner_id in customer_partner_ids:
            if not partner_id.with_context(active_test=True).calendar_verify_availability(date_start, date_end):
                return_vals.update({
                    'success': False,
                    'message': 'It appears you have already selected us a meeting with us on this date.'
                })
                return date_start, date_end, return_vals
        return date_start, date_end, return_vals

    def _get_package_list_desc(self):
        packages = []
        # These code is a patch for old approach so it might look stupid
        package_ids = request.env['service.packages'].sudo().search([('package_type', '=', 'finance_appointment')])
        for package_id in package_ids:
            packages += [{
                'quantity': package_id.quantity,
                'name': package_id.name,
                'price': int(package_id.price),
                'desc': package_id.description,
                'discount_tag': dict(package_id.sudo()._fields['discount_tag'].selection).get(package_id.discount_tag),
            }]

        return packages

    def _split_partner_name(self, partner_data):
        if partner_data.get('name', False):
            name = partner_data.get('name').split()
            if len(name) > 1:
                partner_data['fname'] = name[0]
                partner_data['lname'] = name[-1]
            elif len(name) == 1:
                partner_data['fname'] = name[0]
        return partner_data

    def _get_package_desc(self, package_id):
        if package_id:
            return {
                'quantity': package_id.quantity,
                'name': package_id.name,
                'price': package_id.price,
                'desc': package_id.description,
                'discount_tag': dict(package_id.sudo()._fields['discount_tag'].selection).get(package_id.discount_tag)
            }
        return {
            'error': True
        }

    def _check_site_restriction(self, path):
        page_id = request.env['website.page'].search(
            [('url', '=', path), ('website_id', '=', request.website.id)], limit=1)
        return page_id and page_id.view_id or False
