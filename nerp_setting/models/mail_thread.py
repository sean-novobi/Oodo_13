# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

import datetime
import email
import re
import socket
from odoo import _, api, exceptions, fields, models, tools

from odoo.tools import formataddr
from email.message import Message
from odoo.tools.safe_eval import safe_eval
import json

import logging
_logger = logging.getLogger(__name__)

from odoo.addons.mail.models.mail_thread import MailThread

class MailThreadInherit(models.AbstractModel):
    _inherit = 'mail.thread'

    #################################################
    # Modified by Van Tran
    #   Get Alias Mail based on Email From and filtered them based on the Blacklist
    #   There are two rules:
    #       1. Global rules: when the models in the blacklist is empty
    #       2. On models: blacklist only applied on configured models
    #
    #   email_from_domain: Domain of sender
    #   email_from_fullparts: Email of sender (without sender name)
    #
    #################################################
    def get_dest_aliases_apply_blacklist(self, email_from_domain, email_from_fullparts, rcpt_tos_fullparts, message_dict):
        # GLOBAL RULES
        blacklist_domain = self.env['mail.blacklist.domain'].sudo().search([('domain', '=ilike', email_from_domain),('model_ids','=',False)])
        if blacklist_domain:
            dest_aliases = []
            if not blacklist_domain.exception_rule:
                return dest_aliases
            else:
                if any(value.lower() in message_dict.get(key, '').lower() for key, value in json.loads(blacklist_domain.exception_rule).items()):
                    dest_aliases = self.env['mail.alias'].sudo().search([]).filtered(lambda da: da.alias_completed_email in rcpt_tos_fullparts)
                return dest_aliases

        blacklist_mail = self.env['mail.blacklist.mail'].sudo().search([('email', '=ilike', email_from_fullparts),('model_ids','=',False)])
        if blacklist_mail:
            return []
        # CHECK RULES ON MODELS
        blacklist_on_models = []
        blacklist_domain = self.env['mail.blacklist.domain'].sudo().search([('domain', '=ilike', email_from_domain),('model_ids','!=',False)])
        for domain in blacklist_domain:
            for model in domain.model_ids:
                blacklist_on_models.append(model.id)
        blacklist_mail = self.env['mail.blacklist.mail'].sudo().search([('email', '=ilike', email_from_fullparts),('model_ids','!=',False)])
        for mail in blacklist_mail:
            for model in mail.model_ids:
                blacklist_on_models.append(model.id)
        dest_aliases = self.env['mail.alias'].sudo().search([('alias_model_id', 'not in', blacklist_on_models)]).filtered(lambda da: da.alias_completed_email in rcpt_tos_fullparts)
        return dest_aliases


class MailThreadOverride(MailThread):
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:

         * if the message replies to an existing thread by having a Message-Id
           that matches an existing mail_message.message_id, we take the original
           message model/thread_id pair and ignore custom_value as no creation will
           take place;
         * look for a mail.alias entry matching the message recipients and use the
           corresponding model, thread_id, custom_values and user_id. This could
           lead to a thread update or creation depending on the alias;
         * fallback on provided ``model``, ``thread_id`` and ``custom_values``;
         * raise an exception as no route has been found

        :param string message: an email.message instance
        :param dict message_dict: dictionary holding parsed message variables
        :param string model: the fallback model to use if the message does not match
            any of the currently configured mail aliases (may be None if a matching
            alias is supposed to be present)
        :type dict custom_values: optional dictionary of default field values
            to pass to ``message_new`` if a new record needs to be created.
            Ignored if the thread record already exists, and also if a matching
            mail.alias was found (aliases define their own defaults)
        :param int thread_id: optional ID of the record/thread from ``model`` to
            which this mail should be attached. Only used if the message does not
            reply to an existing thread and does not match any mail alias.
        :return: list of routes [(model, thread_id, custom_values, user_id, alias)]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        fallback_model = model

        # get email.message.Message variables for future processing
        local_hostname = socket.gethostname()
        message_id = message_dict['message_id']

        # compute references to find if message is a reply to an existing thread
        thread_references = message_dict['references'] or message_dict['in_reply_to']
        msg_references = [ref for ref in tools.mail_header_msgid_re.findall(thread_references) if 'reply_to' not in ref]
        mail_messages = self.env['mail.message'].sudo().search([('message_id', 'in', msg_references)], limit=1, order='id desc, message_id')
        is_a_reply = bool(mail_messages)
        reply_model, reply_thread_id = mail_messages.model, mail_messages.res_id

        # author and recipients
        email_from = message_dict['email_from']
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = message_dict['to']
        email_to_localpart = (tools.email_split(email_to) or [''])[0].split('@', 1)[0].lower()
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.

        email_from_fullparts = (tools.email_split(email_from) or [''])[0].lower()
        email_from_domain = (tools.email_split(email_from) or [''])[0].split('@', 1)[1].lower()
        rcpt_tos_localparts = [e.split('@')[0].lower() for e in tools.email_split(message_dict['recipients'])]
        rcpt_tos_fullparts = [e for e in tools.email_split(message_dict['recipients'])]

        # 0. Handle bounce: verify whether this is a bounced email and use it to collect bounce data and update notifications for customers
        #    Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
        #       group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID 
        #    Bounce message (not alias)
        #       See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #        As all MTA does not respect this RFC (googlemail is one of them),
        #       we also need to verify if the message come from "mailer-daemon"
        #    If not a bounce: reset bounce information
        if bounce_alias and bounce_alias in email_to_localpart:
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                self._routing_handle_bounce(message, message_dict)
                return []
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            self._routing_handle_bounce(message, message_dict)
            return []
        self._routing_reset_bounce(message, message_dict)

        # 1. Handle reply
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        if reply_model and reply_thread_id:
            other_alias = self.env['mail.alias'].search([
                '&',
                ('alias_name', '!=', False),
                ('alias_name', '=', email_to_localpart)
            ])
            if other_alias and other_alias.alias_model_id.model != reply_model:
                is_a_reply = False
        if is_a_reply:
            dest_aliases = self.env['mail.alias'].search([('alias_name', 'in', rcpt_tos_localparts)], limit=1)

            user_id = self._mail_find_user_for_gateway(email_from, alias=dest_aliases).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (reply_model, reply_thread_id, custom_values, user_id, dest_aliases),
                raise_exception=False)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, reply_model, reply_thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 2. Handle new incoming email by checking aliases and applying their settings
        if rcpt_tos_localparts:

            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and catchall_alias in email_to_localpart:
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env.ref('mail.mail_bounce_catchall').render({
                    'message': message,
                }, engine='ir.qweb')
                self._routing_create_bounce_email(email_from, body, message, reply_to=self.env.company.email)
                return []

            #################################################
            # Modified by Van Tran
            #   Filter all Aliases by both name and domain instead of only name
            #       to support multiple domains for multi companies
            #
            #   rcpt_tos_fullparts: Recipient full email, be used to to filter Aliases
            #   dest_aliases: List of recipient email which will be used to route emails to correct models
            #
            #################################################
            dest_aliases = self.get_dest_aliases_apply_blacklist(email_from_domain, email_from_fullparts, rcpt_tos_fullparts, message_dict)
            # if not dest_aliases:
            #     dest_aliases = self.env['mail.alias'].search(['alias_name', 'in', rcpt_tos_localparts])
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = self._mail_find_user_for_gateway(email_from, alias=alias).id or self._uid
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, safe_eval(alias.alias_defaults), user_id, alias)
                    route = self._routing_check_route(message, message_dict, route, raise_exception=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 3. Fallback to the provided parameters, if they work
        if fallback_model:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)
            user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (fallback_model, thread_id, custom_values, user_id, None),
                raise_exception=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                    email_from, email_to, message_id, fallback_model, thread_id, custom_values, user_id)
                return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )

    # Override method
    MailThread.message_route = message_route
