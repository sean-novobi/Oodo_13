# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

{
    'name': 'NOVOBI CRM',
    'version': '1.0',
    'website': 'https://www.novobi.com',
    'category': '',
    'author': 'Novobi LLC',
    'depends': [
        'nerp_setting', 'crm', 'website_crm',
    ],
    'description': """
======================
NOVOBI CRM
======================

This module is designed and developed in order to manage and communicate with CRM and Website CRM in Odoo.
""",
    'data': [
        'data/notify_novobi_admin_when_lead_created.xml',
        'data/customer_confirmation_email.xml',

        'security/ir.model.access.csv',

        'views/crm_lead_views.xml',
        'views/res_config_setting_views.xml',
        'views/compliance_type_views.xml',
        'views/industry_type_views.xml',
        'views/interest_type_views.xml',
        'views/odoo_level_views.xml',
        'views/opportunity_task_tag_views.xml',
    ],
    'images': [],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
    'qweb': [
    ],
}
