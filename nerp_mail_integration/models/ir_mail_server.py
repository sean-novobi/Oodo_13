# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import _, api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def _get_default_bounce_receiver_address(self):
        '''Compute the default bounce address.

        The default bounce address is used to set the receiver address.
        It is formed by properly joining the parameters "mail.bounce.alias" and
        "mail.catchall.domain".

        If "mail.bounce.alias" is not set it defaults to "contact".

        If "mail.catchall.domain" is not set, return None.

        '''
        get_param = self.env['ir.config_parameter'].sudo().get_param
        postmaster = get_param('nerp.mail.bounce.receiver.alias', default='contact')
        domain = get_param('mail.catchall.domain')
        if postmaster and domain:
            return '%s@%s' % (postmaster, domain)