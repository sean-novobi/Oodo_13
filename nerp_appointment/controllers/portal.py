# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2018 Novobi LLC (<http://novobi.com>)
#
##############################################################################
import werkzeug

from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import http
from odoo.http import request
import logging
from datetime import datetime, timedelta

class NERPPaymentProcessing(PaymentProcessing):

    ##############################################################################
    # Redirect customer to Summary page of Online Scheduling
    # The url will be got from Session which was added when creating the sale order
    #   in check-out controller
    ##############################################################################

    @http.route()
    def payment_status_page(self, **kwargs):

        res = super(NERPPaymentProcessing, self).payment_status_page(**kwargs)
        if request.session.get('appointment_success_url', False):
            # tx_ids_list = self.get_payment_transaction_ids()
            # payment_transaction_ids = request.env['payment.transaction'].sudo().search([
            #     ('id', 'in', list(tx_ids_list)),
            #     ('date', '>=', (datetime.now() - timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
            # ])
            # tx_to_process = payment_transaction_ids.filtered(lambda x: x.state == 'done' and x.is_processed is False)
            # tx_to_process._post_process_after_done()
            return request.redirect(request.session.get('appointment_success_url'))

        return res