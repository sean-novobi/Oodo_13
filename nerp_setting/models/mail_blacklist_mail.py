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

class MailBlacklistMail(models.Model):
    _name = 'mail.blacklist.mail'
    _description = 'Mail Black List Incoming'

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Blacklist Email', required=True)
    model_ids = fields.Many2many('ir.model', string='Apply on models', help='Models which the blacklist email is applied on')
    active = fields.Boolean(default=True)
    