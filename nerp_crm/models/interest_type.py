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


class InterestType(models.Model):
    _name = 'interest.type'
    _description = 'Interest Type'

    name = fields.Char(string="Interest Type")
    description = fields.Text(string="Description")

    @api.constrains('name')
    def check_interest_name(self):
        for record in self:
            if self.env['interest.type'].search_count([('name', '=ilike', record.name)]) > 1:
                raise ValidationError(_('The interest type already exists!'))
