# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import http, _
import requests as rq
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class ReCaptchaService:

    def verify_capcha(self, kwargs):
        IR_Config = request.env['ir.config_parameter'].sudo()
        if IR_Config.get_param('recaptchav3'):
            response = rq.post('https://www.google.com/recaptcha/api/siteverify', data={
                'secret': IR_Config.get_param('recaptchav3._secret_key'),
                'response': kwargs.get('g-recaptcha-response') or ''
            })
            return response.json()
        else:
            vals = {
                    "recaptcha_disabled": True,
                    "error-msg": "recaptchav3_not_enabled"}
            return vals
