import logging

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.addons.crm.models import crm_stage

_logger = logging.getLogger(__name__)

CRM_LEAD_FIELDS_TO_MERGE = [
    'name',
    'partner_id',
    'campaign_id',
    'company_id',
    'country_id',
    'team_id',
    'state_id',
    'stage_id',
    'medium_id',
    'source_id',
    'user_id',
    'title',
    'city',
    'contact_name',
    'description',
    'mobile',
    'partner_name',
    'phone',
    'probability',
    'planned_revenue',
    'street',
    'street2',
    'zip',
    'create_date',
    'date_action_last',
    'email_from',
    'email_cc',
    'website',
    'partner_name']

# Those values have been determined based on benchmark to minimise
# computation time, number of transaction and transaction time.
PLS_COMPUTE_BATCH_STEP = 50000  # odoo.models.PREFETCH_MAX = 1000 but larger cluster can speed up global computation
PLS_UPDATE_BATCH_STEP = 5000


class Lead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides crm_lead message_new that is called by the mailgateway
            through message_process originated from mail_thread.
            This override updates the default when fetch sent email to new lead.
        """

        # remove external users
        if self.env.user.has_group('base.group_portal'):
            self = self.with_context(default_user_id=False)

        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.

        if self._uid == self.env.ref('base.user_root').id:
            self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        if msg_dict['send_mail']:
            if msg_dict['new_send_mail']:
                defaults = {
                    'name': msg_dict.get('subject') or _("No Subject"),
                    'email_from': tools.email_split(msg_dict.get('to'))[0],
                    'partner_id': '',
                    'contact_name': '',
                }
            else:
                defaults = {
                    'name': msg_dict.get('subject') or _("No Subject"),
                    'email_from': tools.email_split(msg_dict.get('to'))[0],
                    'partner_id': msg_dict.get('author_id', False),
                }

        else:
            defaults = {
                'name': msg_dict.get('subject') or _("No Subject"),
                'email_from': tools.email_split(msg_dict.get('from'))[0],
                'partner_id': msg_dict.get('author_id', False),
            }
            if msg_dict.get('author_id'):
                defaults.update(self._onchange_partner_id_values(msg_dict.get('author_id')))
            if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
                defaults['priority'] = msg_dict.get('priority')
            defaults.update(custom_values)

       # assign right company
        if 'company_id' not in defaults and 'team_id' in defaults:
            defaults['company_id'] = self.env['crm.team'].browse(defaults['team_id']).company_id.id
        return super(Lead, self).message_new(msg_dict, custom_values=defaults)
