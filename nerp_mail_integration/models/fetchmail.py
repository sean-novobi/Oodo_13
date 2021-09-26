import logging
import poplib
import re, datetime
import imaplib
import email
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
from poplib import POP3, POP3_SSL

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import pycompat, ustr
from odoo.tools.misc import clean_context, split_every


_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

# Workaround for Python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536

class MailServer (models.Model):
    """Inherit fetchmail.server to create leads from incoming emails with self-defined rules

        Create fetch_mail_sent method to fetch outgoing emails sent from mail clients into Odoo"""
    _inherit = 'fetchmail.server'

    email_label = fields.Char(string='Email Label', help="Labels' name should be separated by commas")
    email_status_restore = fields.Boolean('Email Status Restore', help="Server will restore the original status of emails after fetching")
    alias_name = fields.Char('Alias Name', help="The name of the email alias, e.g. 'jobs' if you want to catch emails for <jobs@example.odoo.com>")
    alias_domain = fields.Char('Alias domain', compute='_get_alias_domain', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
    fetch_spam_mailbox = fields.Boolean(string='Featch Spam Mailbox',
                                        help='Allow the Incoming Mail Server reading the Spam Mailbox, to prevent missing emails')

    @api.onchange('server_type')
    def onchange_server_type(self):
        if self.server_type != 'imap':
            self.fetch_spam_mailbox = False

    def _get_alias_domain(self):
        alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        for record in self:
            record.alias_domain = alias_domain

    def get_msg_dict(self, message, additionnal_context=None, original=None):
        MailThread = self.env['mail.thread']
        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        message = email.message_from_bytes(message)
        msg_dict = MailThread.with_context(**additionnal_context).message_parse(message, save_original=original)
        return msg_dict

    def get_labeled_emails(self, labels, imap_server, search_date, additionnal_context, server_original):
        label_msg_id = []
        for label in labels:
            if bool(re.search('\s', label)):
                imap_server.select("\"" + label + "\"")
            else:
                imap_server.select(label)
            result, label_data = imap_server.search(None, '(ALL)', '(SENTSINCE {0})'.format(search_date))
            for num in label_data[0].split():
                result, data = imap_server.fetch(num, '(RFC822)')
                message = data[0][1]
                msg_dict = self.get_msg_dict(message, additionnal_context, server_original)
                msg_id = msg_dict['message_id']
                label_msg_id.append(msg_id)
        return label_msg_id

    def fetch_mail(self):
        """ WARNING: meant for cron usage only - will commit() after each email! """
        additionnal_context = {
            'fetchmail_cron_running': True
        }
        MailThread = self.env['mail.thread']
        for server in self:
            _logger.info('start checking for new emails on %s server %s', server.server_type, server.name)
            additionnal_context['default_fetchmail_server_id'] = server.id
            additionnal_context['server_type'] = server.server_type
            count, failed = 0, 0
            imap_server = None
            pop_server = None

            if server.email_label:
                labels = [x.strip() for x in server.email_label.split(',')]  # get all labels' name
            else:
                labels = []

            imap_server = server.connect()
            search_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
            alias_name = server.alias_name

            if server.server_type == 'imap':
                if server.fetch_spam_mailbox:
                    try:
                        imap_server.select(mailbox='[Gmail]/Spam', readonly=False)
                        result, data = imap_server.search(None, '(UNSEEN)')
                        for num in data[0].split():
                            res_id = None
                            result, data = imap_server.fetch(num, '(RFC822)')
                            imap_server.store(num, '-FLAGS', '\\Seen')
                            try:
                                res_id = MailThread.with_context(**additionnal_context).message_process(
                                    server.object_id.model, data[0][1], save_original=server.original,
                                    strip_attachments=(not server.attach))
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.server_type,
                                             server.name, exc_info=True)
                                failed += 1
                            imap_server.store(num, '+FLAGS', '\\Seen')
                            self._cr.commit()
                            count += 1
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count,
                                     server.server_type, server.name, (count - failed), failed)
                    except Exception:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type,
                                     server.name, exc_info=True)

                if not server.email_status_restore:
                    try:
                        imap_server.select()
                        result, data = imap_server.search(None, '(UNSEEN)', '(SENTSINCE {0})'.format(search_date))
                        for num in data[0].split():
                            res_id = None
                            result, data = imap_server.fetch(num, '(RFC822)')
                            imap_server.store(num, '-FLAGS', '\\Seen')
                            try:
                                res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, data[0][1], alias_name, save_original=server.original, strip_attachments=(not server.attach), server_user=server.user)
                                if res_id:
                                    self.env['mail.message'].sudo().search([('res_id', '=', res_id)]).write({'send_to': tools.email_split(msg_dict['to'])[0]})
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.server_type,
                                             server.name, exc_info=True)
                                failed += 1
                            imap_server.store(num, '+FLAGS', '\\Seen')
                            self._cr.commit()
                            count += 1
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count,
                                     server.server_type, server.name, (count - failed), failed)
                    except Exception:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type,
                                     server.name, exc_info=True)
                    finally:
                        if imap_server:
                            imap_server.close()
                            imap_server.logout()
                else:
                    try:
                        # Get all incoming emails and unread emails:
                        imap_server.select()
                        result1, receive_data = imap_server.search(None, '(TO {0})'.format(server.user), '(SENTSINCE {0})'.format(search_date))
                        result2, unread_data = imap_server.search(None, '(UNSEEN)', '(SENTSINCE {0})'.format(search_date))

                        # Get all labeled emails with their message ids
                        label_msg_id = self.get_labeled_emails(labels, imap_server, search_date, additionnal_context, server.original)

                        # Fetch incoming emails:
                        imap_server.select()
                        for num in receive_data[0].split():
                            res_id = None
                            result, data = imap_server.fetch(num, '(RFC822)')
                            message = data[0][1]
                            msg_dict = self.get_msg_dict(message, additionnal_context, server.original)
                            msg_id = msg_dict['message_id']
                            ref = msg_dict['references']

                            # incoming email is a reply email to labeled email or a labeled email
                            if (msg_id in label_msg_id) or (set(ref.split()) & set(label_msg_id)):
                                imap_server.store(num, '-FLAGS', '\\Seen')
                                try:
                                    res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, data[0][1], alias_name, save_original=server.original, strip_attachments=(not server.attach), server_user=server.user)
                                    if res_id:
                                        self.env['mail.message'].sudo().search([('res_id', '=', res_id)]).write({'send_to': tools.email_split(msg_dict['to'])[0]})
                                except Exception:
                                    _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                                    failed += 1
                                imap_server.store(num, '+FLAGS', '\\Seen')
                                self._cr.commit()
                                count += 1
                            else:
                                continue

                        for num in unread_data[0].split():
                            imap_server.store(num, '-FLAGS', '\\Seen')
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.server_type, server.name, (count - failed), failed)
                        imap_server.close()

                    except Exception:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                    finally:
                        if imap_server:
                            imap_server.logout()

            elif server.server_type == 'pop':
                try:
                    while True:
                        pop_server = server.connect()
                        (num_messages, total_size) = pop_server.stat()
                        pop_server.list()
                        for num in range(1, min(MAX_POP_MESSAGES, num_messages) + 1):
                            (header, messages, octets) = pop_server.retr(num)
                            message = (b'\n').join(messages)
                            res_id = None
                            try:
                                res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, message, save_original=server.original, strip_attachments=(not server.attach), server_user=server.user)
                                pop_server.dele(num)
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                                failed += 1
                            self.env.cr.commit()
                        if num_messages < MAX_POP_MESSAGES:
                            break
                        pop_server.quit()
                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", num_messages, server.server_type, server.name, (num_messages - failed), failed)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type, server.name, exc_info=True)
                finally:
                    if pop_server:
                        pop_server.quit()

            server.write({'date': fields.Datetime.now()})
        return True


    @api.model
    def _fetch_mails_sent(self):
        """ Method called by cron to fetch mails sent from servers """
        return self.search([('state', '=', 'done'), ('server_type', 'in', ['pop', 'imap'])]).fetch_mails_sent()

    def fetch_mails_sent(self):
        """ WARNING: meant for cron usage only - will commit() after each email! """
        additionnal_context = {
            'fetchmail_cron_running': True
        }
        MailThread = self.env['mail.thread']
        for server in self:
            _logger.info('start checking for new emails on %s server %s', server.server_type, server.name)
            additionnal_context['default_fetchmail_server_id'] = server.id
            additionnal_context['server_type'] = server.server_type
            count, failed = 0, 0
            imap_server = None
            pop_server = None

            if server.email_label:
                labels = [x.strip() for x in server.email_label.split(',')]  # get all labels' name
            else:
                continue

            imap_server = server.connect()
            search_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
            alias_name = server.alias_name

            if server.server_type == 'imap':
                try:
                    # Get all labeled emails with their message ids
                    label_msg_id = self.get_labeled_emails(labels, imap_server, search_date, additionnal_context, server.original)

                    # Get all sent emails:
                    imap_server.select('"[Gmail]/Sent Mail"')
                    result1, sent_data = imap_server.search(None, '(FROM {0})'.format(server.user), '(SENTSINCE {0})'.format(search_date))

                    for num in sent_data[0].split():
                        res_id = None
                        result, data = imap_server.fetch(num, '(RFC822)')
                        message = data[0][1]
                        msg_dict = self.get_msg_dict(message, additionnal_context, server.original)
                        msg_id = msg_dict['message_id']
                        ref = msg_dict['references']

                        # incoming email is a reply email to labeled email or a labeled email
                        if (msg_id in label_msg_id) or (set(ref.split()) & set(label_msg_id)):
                            try:
                                res_id = MailThread.with_context(**additionnal_context).message_process(server.object_id.model, data[0][1], alias_name, save_original=server.original, strip_attachments=(not server.attach), server_user=server.user)
                                if res_id:
                                    self.env['mail.message'].sudo().search([('res_id', '=', res_id)]).write({'send_to': tools.email_split(msg_dict['to'])[0]})
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.server_type, server.name, exc_info=True)
                                failed += 1
                            self._cr.commit()
                            count += 1
                        else:
                            continue

                    _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.server_type, server.name, (count - failed), failed)
                    imap_server.close()

                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.server_type,
                                 server.name, exc_info=True)
                finally:
                    if imap_server:
                        imap_server.logout()
            server.write({'date': fields.Datetime.now()})
        return True

    @api.model
    def _update_cron(self):
        if self.env.context.get('fetchmail_cron_running'):
            return
        try:
            # Enabled/Disable cron based on the number of 'done' server of type pop or imap
            cron = self.env.ref('fetchmail.ir_cron_mail_gateway_action')
            sent_cron = self.env.ref('fetchmail.ir_cron_sent_mail_gateway_action')
            cron.toggle(model=self._name, domain=[('state', '=', 'done'), ('server_type', 'in', ['pop', 'imap'])])
            sent_cron.toggle(model=self._name, domain=[('state', '=', 'done'), ('server_type', 'in', ['pop', 'imap'])])
        except ValueError:
            pass
