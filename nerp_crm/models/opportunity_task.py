# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class OpportunityTask(models.Model):
    _name = "opportunity.task"
    _description = 'Opportunity Tasks'

    name = fields.Many2one('opportunity.task.tag', string='Task', help='The task tag for Task.')
    lead_id = fields.Many2one('crm.lead', string='Lead/Opportunity')
    status = fields.Boolean(string='Status', help='The status of task. It have two state: Todo and Done.')
    date = fields.Date(string='Date', help='The date planned for the task.')
