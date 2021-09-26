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


class OdooLevel(models.Model):
    _name = 'odoo.level'
    _description = 'Odoo Level'

    name = fields.Char(string="Odoo Level")
    description = fields.Text(string="Description")

    @api.constrains('name')
    def check_odoo_level(self):
        for record in self:
            if self.env['odoo.level'].search_count([('name', '=ilike', record.name)]) > 1:
                raise ValidationError(_('The odoo level already exists!'))
