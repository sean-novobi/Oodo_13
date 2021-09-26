# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import http, _, fields
import requests as rq
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class RecaptchaController(http.Controller):

    @http.route([
        '/recaptchav3/site_key',
    ], type='json', auth="public", website=True)
    def get_site_key(self, **kwargs):
        vals = {'success': False}
        IR_Config = request.env['ir.config_parameter'].sudo()
        if IR_Config.get_param('recaptchav3'):
            site_key = IR_Config.get_param('recaptchav3._site_key')
            if site_key:
                vals['success'] = True
                vals.update({'site_key': site_key})
            else:
                vals.update({'error-msg': 'site_key_not_declared'})
        else:
            vals.update({'error-msg': 'recaptchav3_not_enabled'})
        return vals

