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
import logging

class IrConfigParameterInherit(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model
    def get_param(self, key, default=False, apply_multi_company=True):
        """Retrieve the value for a given key.

        :param string key: The key of the parameter value to retrieve.
        :param string default: default value if parameter is missing.
        :return: The value of the parameter, or ``default`` if it does not exist.
        :rtype: string
        """
        res = super(IrConfigParameterInherit, self).get_param(key, default)
        if key == 'web.base.url' and apply_multi_company:
            company_id = self.env.company
            if company_id.web_base_url:
                return company_id.web_base_url
        return res

