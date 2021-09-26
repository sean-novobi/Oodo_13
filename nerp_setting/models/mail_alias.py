# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

import logging
from odoo import _, api, fields, models

class Alias(models.Model):
    _inherit = 'mail.alias'

    custom_alias_domain = fields.Char(string='Custom Alias Domain', help='Used to compute alias domain')
    alias_completed_email = fields.Char(string='Alias Completed Email', compute='_compute_alias_completed_email', help='Used to get fully email of Mail Alias')

    def _get_alias_domain(self):
        default_alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        for record in self:
            alias_domain = default_alias_domain
            if record.alias_parent_model_id and record.alias_parent_thread_id:
                if 'company_id' in self.env[record.alias_parent_model_id.model]._fields:
                    parent_record = self.env[record.alias_parent_model_id.model].browse(record.alias_parent_thread_id)
                    if parent_record.company_id and parent_record.company_id.alias_domain:
                        alias_domain = parent_record.company_id.alias_domain
            if record.custom_alias_domain:
                alias_domain = record.custom_alias_domain
            record.alias_domain = alias_domain

    @api.depends()
    def _compute_alias_completed_email(self):
        for record in self:
            if record.alias_name:
                record.alias_completed_email = record.alias_name +'@'+record.alias_domain
            else:
                record.alias_completed_email = ''

    @api.model
    def _clean_and_make_unique(self, name, alias_ids=False):
        if name in ['info','support', 'contact']:
            return name
        else:
            return super(Alias, self)._clean_and_make_unique(name, alias_ids)

    @api.model
    def _delete_unique_alias_mail(self):
        self.env.cr.execute("""
            ALTER TABLE mail_alias DROP CONSTRAINT mail_alias_alias_unique;
        """)