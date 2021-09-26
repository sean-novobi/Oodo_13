# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from urllib.parse import urlparse


class Lead(models.Model):
    _inherit = "crm.lead"

    def _get_default_sales_team(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        default_sale_team_id = IrConfig.get_param('nerp_sales_team_id', False)
        return int(default_sale_team_id)

    def _default_opportunity_tasks(self):
        oppor_task_tags = self.env['opportunity.task.tag'].search([('is_default_tag', '=', True)])
        return [(0, 0, {'name': tag.id, 'status': False}) for tag in oppor_task_tags]

    note_url = fields.Char(string="Questionnaire URL", help="Open the meeting notes on wiki page related to this customer")
    project_est_url = fields.Char(string="Project Estimate URL")
    activity_date_deadline = fields.Date(store=True)
    team_id = fields.Many2one(default=_get_default_sales_team)
    guests_emails = fields.Char(string="Guests Emails")

    # Reporting Tab
    in_stagnant = fields.Boolean(string='In Stagnant')
    interest_type = fields.Many2one('interest.type', string='Interest')
    odoo_level = fields.Many2one('odoo.level', string='Odoo Level')
    compliance_types = fields.Many2many('compliance.type', string='Compliance')
    industry_types = fields.Many2many('industry.type', string='Industry')

    # Opportunity Tasks Tab
    opportunity_tasks = fields.One2many('opportunity.task', 'lead_id', string='Opportunity Tasks',
                                        default=_default_opportunity_tasks,
                                        help='Add a table to help the user to manage tasks for Lead/Opportunity')
    # Meeting recording Tab
    meeting_recording = fields.One2many('meeting.recording', 'lead_id', string='Meeting Recording',
                                        help='Add a table to help user saving meeting recording on CRM')

    # Override func _notify_get_groups in odoo.addons.crm.models.crm_lead
    def _notify_get_groups(self, msg_vals=None):
        """ Handle salesman recipients that can convert leads into opportunities
        and set opportunities as won / lost. """
        groups = super(Lead, self)._notify_get_groups(msg_vals=msg_vals)
        local_msg_vals = dict(msg_vals or {})

        self.ensure_one()
        if self.type == 'lead':
            convert_action = self._notify_get_action_link('controller', controller='/lead/convert', **local_msg_vals)
            salesman_actions = [{'url': convert_action, 'title': _('Convert to opportunity')}]
        else:
            won_action = self._notify_get_action_link('controller', controller='/lead/case_mark_won', **local_msg_vals)
            lost_action = self._notify_get_action_link('controller', controller='/lead/case_mark_lost', **local_msg_vals)
            salesman_actions = [
                {'url': won_action, 'title': _('Won')},
                {'url': lost_action, 'title': _('Lost')}]

        if self.team_id:
            custom_params = dict(local_msg_vals, res_id=self.team_id.id, model=self.team_id._name)
            salesman_actions.append({
                'url': self._notify_get_action_link('view', **custom_params),
                'title': _('Sales Team Settings')
            })

        ###############################################
        # Customize by Tri Nguyen
        # Change the domain in internal email to https://erp.novobi.com instead of based on company
        ###############################################
        if salesman_actions:
            for saleman_action in salesman_actions:
                url = "https://erp.novobi.com" + urlparse(saleman_action.get('url')).path + "?" + urlparse(
                    saleman_action.get('url')).query
                saleman_action.update({'url': url})

        salesman_group_id = self.env.ref('sales_team.group_sale_salesman').id
        new_group = (
            'group_sale_salesman', lambda pdata: pdata['type'] == 'user' and salesman_group_id in pdata['groups'], {
                'actions': salesman_actions,
            })

        return [new_group] + groups


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    @api.model
    def action_your_pipeline(self):
        action = super(CrmTeam, self).action_your_pipeline()
        IrConfig = self.env['ir.config_parameter'].sudo()
        default_sale_team_id = IrConfig.get_param('nerp_sales_team_id', False)
        if default_sale_team_id:
            action.get('context').update({'default_team_id': int(default_sale_team_id)})
        return action
