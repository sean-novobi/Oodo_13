# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MeetingRecording(models.Model):
    _name = "meeting.recording"
    _description = 'Meeting Recording'

    name = fields.Selection([('internal', 'Internal'), ('external', 'External')], string='Meeting Type',
                            help='Meeting type for the meeting. E.g: Internal, External, ...')
    description = fields.Char(string='Topics', help='The topic of the meeting. E.g: Kick off, Transfer, ...')
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity')
    url = fields.Text(string='URL', help='The URL which saving the url of the meeting recording.')
    date = fields.Date(string='Date', help='The date on which the meeting took place.')
    members = fields.Many2many('res.partner', string='Members', help='Members attend the meeting.')
