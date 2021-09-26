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

class ResConfigSettings(models.Model):
    _inherit = 'res.company'

    email_reply_to = fields.Char(string='Email Reply To', help='Used on email templates to support multi companies setup instead of using default alias domain.')
    alias_domain = fields.Char(string='Alias Domain', help='Used on models which use multiple domains for incoming emails')
    web_base_url = fields.Char(string='Web Base URL', help='Used to override the get_param function, give the value in company level, to support multiple domains in one instance')

