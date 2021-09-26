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


class ComplianceType(models.Model):
    _name = 'compliance.type'
    _description = 'Compliance Type'

    name = fields.Char(string="Compliance Type")
    description = fields.Text(string="Description")

    @api.constrains('name')
    def check_compliance_name(self):
        for record in self:
            if self.env['compliance.type'].search_count([('name', '=ilike', record.name)]) > 1:
                raise ValidationError(_('The compliance type already exists!'))
