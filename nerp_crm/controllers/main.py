# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_form.controllers.main import WebsiteForm
import logging

class WebsiteForm(WebsiteForm):

    def insert_record(self, request, model, values, custom, meta=None):
        model_name = model.sudo().model
        if model_name == 'mail.mail':
            custom = "Email: %s \n" % values.get('email_from') + custom

        record_id = super(WebsiteForm, self).insert_record(request, model, values, custom, meta=meta)
        record = request.env[model_name].sudo().browse(record_id)
        logging.warning(record.create_uid.name)
        ################################################################
        #
        # Send a notification to NOVOBI admin when a lead is generated on website
        #
        ################################################################
        if model_name == 'crm.lead' and record_id:
            lead_id = request.env['crm.lead'].sudo().browse(record_id)
            if lead_id:
                template_id = request.env.ref('nerp_crm.notify_novobi_admin_when_lead_created')
                template_id.sudo().send_mail(lead_id.id)
                if 'omniborders' in lead_id.company_id.name.lower():
                    team_name = 'OmniBorders'
                else:
                    team_name = 'Novobi'
                template_id = request.env.ref('nerp_crm.customer_confirmation_email')
                rendering_context = dict(template_id._context)
                rendering_context.update({
                    'team_name': team_name,
                })
                template_id = template_id.with_context(rendering_context)
                template_id.sudo().send_mail(lead_id.id)
        ################################################################
        #
        # If a message is posted on website (from Website form), instead of using
        #   customer email as Sender, we change the Sender to our company email
        #   to pass the restriction of Out Going Mail server
        #
        ################################################################
        if model_name == 'mail.mail' and record_id:
            record = request.env[model_name].sudo().browse(record_id)
            user = request.env.user
            record.email_from = user.company_id.email
            # record.author_id = user
            if not record.subject:
                record.subject = "This message has been posted on %s website!" % user.company_id.name
        return record_id
