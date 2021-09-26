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
from odoo.http import request
import requests
import json
from werkzeug import urls

import logging
_logger = logging.getLogger(__name__)

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


# FIXME : this needs to become an AbstractModel, to be inhereted by google_calendar_service and google_drive_service
class GoogleService(models.TransientModel):
    _inherit = 'google.service'

    @api.model
    def _get_authorize_uri(self, from_url, service, scope=False):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
        """
        state = {
            'd': self.env.cr.dbname,
            's': service,
            'f': from_url
        }

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl', apply_multi_company=False)
        client_id = get_param('google_%s_client_id' % (service,), default=False)

        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': client_id,
            'state': json.dumps(state),
            'scope': scope or '%s/auth/%s' % (GOOGLE_API_BASE_URL, service),  # If no scope is passed, we use service by default to get a default scope
            'redirect_uri': base_url + '/google_account/authentication',
            'approval_prompt': 'force',
            'access_type': 'offline'
        })
        return "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)

    @api.model
    def _get_google_token_json(self, authorize_code, service):
        """ Call Google API to exchange authorization code against token, with POST request, to
            not be redirected.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl', apply_multi_company=False)
        client_id = get_param('google_%s_client_id' % (service,), default=False)
        client_secret = get_param('google_%s_client_secret' % (service,), default=False)

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_account/authentication'
        }
        _logger.info("-------- Google Token Data ---------")
        _logger.info(data)
        try:
            dummy, response, dummy = self._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, type='POST', preuri='')
            return response
        except requests.HTTPError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise self.env['res.config.settings'].get_config_warning(error_msg)
