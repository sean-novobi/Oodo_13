##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2018 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class IndustryType(models.Model):
    _name = 'industry.type'
    _description = 'Industry Type'

    name = fields.Char(string="Industry Type")
    description = fields.Text(string="Description")

    @api.constrains('name')
    def check_industry_name(self):
        for record in self:
            if self.env['industry.type'].search_count([('name', '=ilike', record.name)]) > 1:
                raise ValidationError(_('The industry type already exists!'))
