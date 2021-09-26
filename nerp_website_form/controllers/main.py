# -*- coding: utf-8 -*-

import json
from odoo import http, _, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

from odoo.addons.nerp_recaptcha.services.recaptcha.google_recaptcha import ReCaptchaService
from odoo.addons.website_form.controllers.main import WebsiteForm

class WebsiteFormExtend(WebsiteForm):
    @http.route('/website_form/<string:model_name>', type='http', auth="public", methods=['POST'], website=True)
    def website_form(self, model_name, **kwargs):
        # Recaptcha verification
        IR_Config = request.env['ir.config_parameter'].sudo()
        if IR_Config.get_param('recaptchav3') and kwargs.get('recaptcha', False):
            ReCaptchaObject = ReCaptchaService()
            response = ReCaptchaObject.verify_capcha(kwargs)
            _logger.info("Verifing Google reCaptcha on Customer Website Form...")
            _logger.info(str(response) or 'Something wrong happened')
            # Delete reCaptcha value to prevent Odoo to compute it in record's description
            if request.params.get('g-recaptcha-response', False):
                del request.params['g-recaptcha-response']
            if request.params.get('recaptcha'):
                del request.params['recaptcha']
            if not (response.get('success')
                    and response.get('score') >= float(IR_Config.get_param('recaptchav3._threshold'))
                    and response.get('action') == 'submit_form'):
                if response.get('recaptcha_disabled'):
                    pass
                else:
                    # TODO: make page reload when failed
                    return json.dumps(response)
        return super(WebsiteFormExtend, self).website_form(model_name, **kwargs)