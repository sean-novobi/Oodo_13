# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json

class MailBlacklistDomain(models.Model):
    _name = 'mail.blacklist.domain'
    _description = 'Domain Black List Incoming'

    name = fields.Char(string='Name', required=True)
    domain = fields.Char(string='Blacklist Domain', required=True)
    model_ids = fields.Many2many('ir.model', string='Apply on models', help='Models which the blacklist domain is applied on')
    active = fields.Boolean(default=True)
    exception_rule = fields.Char(
        string='Exception Rule',
        help='Allow the incoming mail server to fetch the email from the blacklist domain with the rule')

    @api.constrains('exception_rule')
    def _check_expetion_rule(self):
        try:
            vals = ['subject', 'from', 'cc', 'body']
            all(key.lower() in vals for key in json.loads(self.exception_rule).keys())
        except Exception:
            raise UserError(_("Please follow the rule."))
