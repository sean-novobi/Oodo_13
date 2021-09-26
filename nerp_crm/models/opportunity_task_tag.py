# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OpportunityTask(models.Model):
    _name = "opportunity.task.tag"
    _description = 'Opportunity Task Tags'

    name = fields.Char(string='Task Tag', help='The task tag for the Task on CRM.')
    is_default_tag = fields.Boolean(string='Default Tag',
                                    help='The new lead will have one task for the tag when it created.')

    @api.constrains('name')
    def _check_task_name(self):
        for record in self:
            if self.env['opportunity.task.tag'].search_count([('name', '=ilike', record.name)]) > 1:
                raise ValidationError(_("Opportunity task tag must be unique."))
