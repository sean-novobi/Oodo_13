# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################
import base64

from odoo import models, fields, api
import json


class CalendarAttendee(models.Model):
    _inherit = "calendar.attendee"

    def _send_mail_to_attendees_of_novobi_appointment(self, template_xmlid, with_ics=True, force_send=False, force_event_id=False):
        """
            This function is a copy of odoo's original function with some modification.
            We add a another paramater with_ics, which will prevent the rendering of ics for specific email
            Please refer to the original function for further details : _send_mail_to_attendees
        """

        res = False

        if with_ics:
            # get ics file for all meetings
            ics_files = force_event_id._get_ics_file() if force_event_id else self.mapped('event_id')._get_ics_file()
        else:
            ics_files = {}

        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get(
                "no_mail_to_attendees"):
            return res

        calendar_view = self.env.ref('calendar.view_calendar_event_calendar')
        invitation_template = self.env.ref(template_xmlid)

        # prepare rendering context for mail template
        colors = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }
        rendering_context = dict(self._context)
        rendering_context.update({
            'color': colors,
            'action_id': self.env['ir.actions.act_window'].search([('view_id', '=', calendar_view.id)], limit=1).id,
            'dbname': self._cr.dbname,
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url',
                                                                         default='https://novobi.com'),
            'force_event_id': force_event_id,
        })
        invitation_template = invitation_template.with_context(rendering_context)

        # send email with attachments
        mail_ids = []
        for attendee in self:
            if attendee.email or attendee.partner_id.email:
                # FIXME: is ics_file text or bytes?
                event_id = force_event_id.id if force_event_id else attendee.event_id.id
                ics_file = ics_files.get(event_id)

                email_values = {
                    'model': None,  # We don't want to have the mail in the tchatter while in queue!
                    'res_id': None,
                }
                if ics_file:
                    email_values['attachment_ids'] = [
                        (0, 0, {'name': 'invitation.ics',
                                'mimetype': 'text/calendar',
                                'datas': base64.b64encode(ics_file)})
                    ]

                # Novobi modification: dont use default motif_layour
                mail_ids.append(invitation_template.send_mail(attendee.id, email_values=email_values))

        if force_send and mail_ids:
            res = self.env['mail.mail'].browse(mail_ids).send()

        return res

    def _send_mail_to_attendees(self, template_xmlid, force_send=False, force_event_id=False):
        """
        Overwrite odoo's default function with the same params, please refer to original function for details
        """

        for attendee in self:
            if attendee.event_id.active:
                if {
                    template_xmlid == "calendar.calendar_template_meeting_invitation" or
                    template_xmlid == "calendar.calendar_template_meeting_changedate" or
                    template_xmlid == "calendar.calendar_template_meeting_reminder" or
                    template_xmlid == "nerp_appointment.finance_calendar_template_meeting_cancel" or
                    template_xmlid == "nerp_appointment.novobi_calendar_template_meeting_cancel"
                }:
                    with_ics = True
                    if template_xmlid == "calendar.calendar_template_meeting_invitation":
                        # TODO: create new new template for novobi.com
                        if attendee.event_id.appointment_type_id.novobi_appointment_type == 'accounting':
                            template_xmlid = "nerp_appointment.finance_calendar_template_meeting_invitation"
                        elif attendee.event_id.appointment_type_id.novobi_appointment_type == 'novobi':
                            template_xmlid = "nerp_appointment.novobi_calendar_template_meeting_invitation"
                    elif template_xmlid == "calendar.calendar_template_meeting_changedate":
                        if attendee.event_id.appointment_type_id.novobi_appointment_type == 'accounting':
                            template_xmlid = "nerp_appointment.finance_calendar_template_meeting_changedate"
                        elif attendee.event_id.appointment_type_id.novobi_appointment_type == 'novobi':
                            template_xmlid = "nerp_appointment.novobi_calendar_template_meeting_changedate"
                    elif template_xmlid == "calendar.calendar_template_meeting_reminder":
                        if attendee.event_id.appointment_type_id.novobi_appointment_type == 'accounting':
                            template_xmlid = "nerp_appointment.finance_calendar_template_meeting_reminder"
                        elif attendee.event_id.appointment_type_id.novobi_appointment_type == 'novobi':
                            template_xmlid = "nerp_appointment.novobi_calendar_template_meeting_reminder"
                    else:
                        with_ics = False
                    # Use fore_send because when attendees are added via backend, we want the email management system to handle everything
                    return self._send_mail_to_attendees_of_novobi_appointment(template_xmlid, with_ics, force_send, force_event_id)
                else:
                    return super(CalendarAttendee, self)._send_mail_to_attendees(template_xmlid, force_send, force_event_id)
            else:
                pass
