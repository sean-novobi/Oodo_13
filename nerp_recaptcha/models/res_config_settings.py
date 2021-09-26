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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recaptchav3 = fields.Boolean(config_parameter='recaptchav3')
    recaptcha_site_key = fields.Char('reCAPTCHAv3 Site Key', config_parameter='recaptchav3._site_key')
    recaptcha_secret_key = fields.Char('reCAPTCHAv3 Secret Key', config_parameter='recaptchav3._secret_key')
    recaptcha_threshold = fields.Float('reCAPTCHAv3 Threshold', config_parameter='recaptchav3._threshold')