# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

import werkzeug.urls
from odoo import api, fields, models, _

from odoo.addons.auth_signup.models.res_partner import ResPartner
import logging


from urllib.parse import urlparse

class ResPartnerInherit(ResPartner):
    # _inherit = 'res.partner'

    def _get_signup_url_for_action(self, url=None, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """
        res = dict.fromkeys(self.ids, False)
        for partner in self:
            base_url = partner.get_base_url()
            if partner.user_ids:
                website_id = self.env['website'].sudo().search([('company_id','=',partner.user_ids[0].company_id.id)], limit=1)
                if website_id and website_id.domain:
                    base_url = "https://" + website_id.domain
            # when required, make sure the partner has a valid signup token
            if self.env.context.get('signup_valid') and not partner.user_ids:
                partner.sudo().signup_prepare()

            route = 'login'
            # the parameters to encode for the query
            query = dict(db=self.env.cr.dbname)
            signup_type = self.env.context.get('signup_force_type_in_url', partner.sudo().signup_type or '')
            if signup_type:
                route = 'reset_password' if signup_type == 'reset' else signup_type

            if partner.sudo().signup_token and signup_type:
                query['token'] = partner.sudo().signup_token
            elif partner.user_ids:
                query['login'] = partner.user_ids[0].login
            else:
                continue        # no signup token, no user, thus no signup url!

            if url:
                query['redirect'] = url
            else:
                fragment = dict()
                base = '/web#'
                if action == '/mail/view':
                    base = '/mail/view?'
                elif action:
                    fragment['action'] = action
                if view_type:
                    fragment['view_type'] = view_type
                if menu_id:
                    fragment['menu_id'] = menu_id
                if model:
                    fragment['model'] = model
                if res_id:
                    fragment['res_id'] = res_id

                if fragment:
                    query['redirect'] = base + werkzeug.urls.url_encode(fragment)

            url = "/web/%s?%s" % (route, werkzeug.urls.url_encode(query))
            if not self.env.context.get('relative_url'):
                url = werkzeug.urls.url_join(base_url, url)
            res[partner.id] = url

        return res

    ResPartner._get_signup_url_for_action = _get_signup_url_for_action


class ResPartnerExtend(models.Model):
    _inherit = 'res.partner'

    _mail_flat_thread = True

