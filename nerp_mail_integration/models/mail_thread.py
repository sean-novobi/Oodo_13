import email
import logging
import re
import socket

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib


from email.message import Message
from odoo import _, api, exceptions, fields, models, tools, registry, SUPERUSER_ID
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)



class MailThreadInherit(models.AbstractModel):
    _inherit = 'mail.thread'
    _description = 'Merge incoming emails with a same email address when create leads'

    @api.model
    def message_process(self, model, message, alias_name, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None, server_user=None):
        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        message = email.message_from_bytes(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg_dict = self.message_parse(message, save_original=save_original)
        if strip_attachments:
            msg_dict.pop('attachments', None)

        existing_msg_ids = self.env['mail.message'].search([('message_id', '=', msg_dict['message_id'])], limit=1)
        if existing_msg_ids:
            _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing',
                         msg_dict.get('email_from'), msg_dict.get('to'), msg_dict.get('message_id'))
            return False

        # find possible routes for the message
        user_email = server_user
        routes = self.message_route(message, msg_dict, alias_name, model, thread_id, custom_values, server_user=user_email)
        thread_id = self._message_route_process(message, msg_dict, routes)
        return thread_id


    def handle_bounce (self, bounce_alias, email_to_localparts, email_to, message, message_dict, bounce_alias_static, email_from_localpart):
        # Handle bounce
        #    Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
        #       group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
        #    Bounce message (not alias)
        #       See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #        As all MTA does not respect this RFC (googlemail is one of them),
        #       we also need to verify if the message come from "mailer-daemon"
        #    If not a bounce: reset bounce information
        if bounce_alias and any(email.startswith(bounce_alias) for email in email_to_localparts):
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)
            if bounce_match:
                self._routing_handle_bounce(message, message_dict)
                return []
        if bounce_alias and bounce_alias_static and any(email == bounce_alias for email in email_to_localparts):
            self._routing_handle_bounce(message, message_dict)
            return []
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            self._routing_handle_bounce(message, message_dict)
            return []

    def handle_duplicate(self, reply_model, reply_thread_id, alias_name, rcpt_tos_valid_localparts, is_a_reply, is_dup, email_from, message, message_dict, custom_values, email_to, message_id, dup_model, dup_thread_id):
        # Handle email address duplication and reply emails
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        if reply_model and reply_thread_id:
            other_model_aliases = self.env['mail.alias'].search([
                '&', '&',
                ('alias_name', '!=', False),
                ('alias_name', '=', alias_name),
                ('alias_model_id.model', '!=', reply_model),
            ])
            if other_model_aliases:
                is_a_reply = False
                rcpt_tos_valid_localparts = [to for to in rcpt_tos_valid_localparts if to in other_model_aliases.mapped('alias_name')]
        if is_dup:
            if is_a_reply:
                dest_aliases = self.env['mail.alias'].search([('alias_name', '=', alias_name), ('alias_model_id.model', '=', reply_model)], limit=1)

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
            else:
                dest_aliases = self.env['mail.alias'].search([('alias_name', '=', alias_name), ('alias_model_id.model', '=', dup_model)], limit=1)
                user_id = self._mail_find_user_for_gateway(email_from, alias=dest_aliases).id or self._uid
                route = self._routing_check_route(
                    message, message_dict,
                    (dup_model, dup_thread_id, custom_values, user_id, dest_aliases),
                    raise_exception=False)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: merge duplicated msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, dup_model, dup_thread_id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []


    def handle_new_incoming_email(self, rcpt_tos_localparts, is_sent, message_dict, catchall_alias, email_to_localparts, email_from, email_to, message_id, message, alias_name):
        # Handle new incoming email by checking aliases and applying their settings
        if rcpt_tos_localparts and not is_sent:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and email_to_localparts and all(email_localpart == catchall_alias for email_localpart in email_to_localparts):
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env.ref('mail.mail_bounce_catchall').render({
                    'message': message,
                }, engine='ir.qweb')
                self._routing_create_bounce_email(email_from, body, message, reply_to=self.env.company.email)
                return []

            dest_aliases = self.env['mail.alias'].search([('alias_name', '=', alias_name)])
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


    def handle_sent_email(self, is_sent, is_sent_current, alias_name, sent_model, email_to, message, message_dict, sent_thread_id, custom_values, email_from, message_id):
        # Handle sent email
        if is_sent:
            message_dict['send_mail'] = True
            if is_sent_current:         # sent email to current lead in db
                dest_aliases = self.env['mail.alias'].search([('alias_name', '=', alias_name), ('alias_model_id.model', '=', sent_model)], limit=1)
                user_id = self._mail_find_user_for_gateway(email_to, alias=dest_aliases).id or self._uid
                route = self._routing_check_route(message, message_dict, (sent_model, sent_thread_id, custom_values, user_id, dest_aliases), raise_exception=False)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: sent msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, sent_model, sent_thread_id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []
            else:             # sent email to new lead:
                message_dict['new_send_mail'] = True
                dest_aliases = self.env['mail.alias'].search([('alias_name', '=', alias_name)])
                if dest_aliases:
                    routes = []
                    for alias in dest_aliases:
                        user_id = self._mail_find_user_for_gateway(email_to, alias=alias).id or self._uid
                        route = (alias.alias_model_id.model, alias.alias_force_thread_id, safe_eval(alias.alias_defaults), user_id, dest_aliases)
                        route = self._routing_check_route(message, message_dict, route, raise_exception=True)
                        if route:
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                                email_from, email_to, message_id, route)
                            routes.append(route)
                    return routes


    def handle_fallback(self, fallback_model, message_dict, email_from, message, thread_id, custom_values, email_to, message_id):
        # Fallback to the provided parameters, if they work
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


    @api.model
    def message_route(self, message, message_dict, alias_name,  model=None, thread_id=None, custom_values=None, server_user=None):
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        bounce_alias_static = tools.str2bool(self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias.static", "False"))
        fallback_model = model

        # get email.message.Message variables for future processing
        local_hostname = socket.gethostname()
        message_id = message_dict['message_id']

        # create send_mail field in message_dict for outgoing mails detection
        message_dict['send_mail'] = False

        # author and recipients
        email_from = message_dict['email_from']
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = message_dict['to']
        email_to_localparts = [e.split('@', 1)[0].lower() for e in (tools.email_split(email_to) or [''])]

        # Extract message info:
        thread_references = message_dict['references'] or message_dict['in_reply_to']
        msg_references = [
            re.sub(r'[\r\n\t ]+', r'', ref)  # "Unfold" buggy references
            for ref in tools.mail_header_msgid_re.findall(thread_references)
            if 'reply_to' not in ref]
        mail_messages = self.env['mail.message'].sudo().search([('message_id', 'in', msg_references)], limit=1, order='id desc, message_id')

        # detect if email is a sent email:
        is_sent_current = True if bool(mail_messages) and bool(email_from_localpart == server_user.split('@')[0]) else False # the same conversation
        is_sent = bool(email_from_localpart == server_user.split('@')[0])
        sent_model, sent_thread_id = mail_messages.model, mail_messages.res_id

        # Handle duplication email addresses (different conversations)
        if is_sent:         # duplication email address of sending mails
            dup_mail_message = self.env['mail.message'].sudo().search([('send_to', '=', tools.email_split(email_to)[0]), ('model', '=', 'crm.lead')], limit=1, order='id desc, message_id') or self.env['mail.message'].sudo().search([('send_to', '=', tools.email_split(message_dict['email_from'])[0]), ('model', '=', 'crm.lead')], limit=1, order='id desc, message_id') # when outgoing is fetched after incoming
        else:               # duplication email address of incoming mails
            dup_mail_message = self.env['mail.message'].sudo().search([('email_from', '=', message_dict['email_from']), ('model', '=', 'crm.lead')], limit=1, order='id desc, message_id') or self.env['mail.message'].sudo().search([('send_to', '=', tools.email_split(message_dict['email_from'])[0]), ('model', '=', 'crm.lead')], limit=1, order='id desc, message_id') # when incoming is fetched after outgoing
        is_dup = bool(dup_mail_message)
        dup_model, dup_thread_id = dup_mail_message.model, dup_mail_message.res_id

        # Check to find if message is a reply to an existing thread
        is_a_reply = True if bool(mail_messages) and bool(email_from_localpart != server_user.split('@')[0]) else False
        reply_model, reply_thread_id = mail_messages.model, mail_messages.res_id

        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos_localparts = [
            e.split('@')[0].lower()
            for e in tools.email_split(message_dict['recipients'])
        ]
        rcpt_tos_valid_localparts = [to for to in rcpt_tos_localparts]

        # 0. Handle bounce: verify whether this is a bounced email and use it to collect bounce data and update notifications for customers
        is_bounce = self.handle_bounce(bounce_alias, email_to_localparts, email_to, message, message_dict, bounce_alias_static, email_from_localpart)
        if is_bounce:
            return is_bounce
        self._routing_reset_bounce(message, message_dict)


        # 1. Handle email address duplication and reply emails
        dup_route = self.handle_duplicate(reply_model, reply_thread_id, alias_name, rcpt_tos_valid_localparts, is_a_reply, is_dup, email_from,
                     message, message_dict, custom_values, email_to, message_id, dup_model, dup_thread_id)
        if dup_route:
            return dup_route


        # 2. Handle new incoming email by checking aliases and applying their settings
        new_route = self.handle_new_incoming_email(rcpt_tos_localparts, is_sent, message_dict, catchall_alias, email_to_localparts,
                                  email_from, email_to, message_id, message, alias_name)
        if new_route:
            return new_route

        # 3. Handle sent email:
        sent_route = self.handle_sent_email(is_sent, is_sent_current, alias_name, sent_model, email_to, message, message_dict,
                          sent_thread_id, custom_values, email_from, message_id)
        if sent_route:
            return sent_route

        # 4. Fallback to the provided parameters, if they work
        fallback = self.handle_fallback(fallback_model, message_dict, email_from, message, thread_id, custom_values, email_to,
                        message_id)
        if fallback:
            return fallback

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )


    def _routing_create_bounce_email(self, email_from, body_html, message, **mail_values):
        bounce_to = self.env['ir.mail_server']._get_default_bounce_receiver_address()
        msg_dict = self.message_parse(message, save_original=True)
        body_html = self.env.ref('nerp_fetchmail.nerp_mail_bounce_catchall_notofication').render({
                    'message': msg_dict,
                }, engine='ir.qweb')
        body_html += bytes(msg_dict.get('body'), 'utf-8')
        bounce_mail_values = {
            'body_html': body_html,
            'subject': 'Re: %s' % msg_dict.get('subject', ''),
            'email_to': bounce_to,
            'auto_delete': False,
        }
        bounce_from = self.env['ir.mail_server']._get_default_bounce_address()
        if bounce_from:
            bounce_mail_values['email_from'] = 'MAILER-DAEMON <%s>' % bounce_from
        bounce_mail_values.update(mail_values)
        self.env['mail.mail'].create(bounce_mail_values)

