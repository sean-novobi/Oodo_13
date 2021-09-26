from odoo import api, fields, models, _


class ResConfigSettingInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_team_id = fields.Many2one('crm.team', string="Default CRM Sales Team", config_parameter='nerp_sales_team_id')
