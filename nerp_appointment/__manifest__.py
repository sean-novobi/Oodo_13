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
    'name': 'NOVOBI ERP - Appointment',
    'version': '1.0',
    'website': 'https://www.novobi.com',
    'category': '',
    'author': 'Novobi LLC',
    'depends': [
        'nerp_setting', 
        'nerp_crm',
        'website_calendar',
        'sale_management',
        'nerp_recaptcha',
        'nerp_website_form',
        'account_accountant',
        'payment_stripe',
        'google_calendar',
        'hr'
    ],
    'description': """
=======================
NOVOBI ERP - Appointment
=======================

This module is designed and developed in order to customize the Odoo Website Calendar - Appointment to allow customer books meeting with NOVOBI staff.
""",
    'data': [
        # Backend views
        'views/assets.xml',
        'views/calendar_appointment_views.xml',
        'views/calendar_views.xml',
        # 'views/website_calendar_templates.xml',
        'views/service_packages_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        
        # Basic templates are used for both finance and novobi
        'views/pages/appointment_form.xml',

        # Finance templates
        'views/pages/finance/finance_form.xml',
        'views/pages/finance/finance_calendar.xml',
        'views/pages/finance/finance_summary.xml',
        'views/pages/finance/finance_packages.xml',
        'views/pages/finance/finance_not_found.xml',
        'views/pages/finance/finance_checkout.xml',

        # Novobi templates
        'views/pages/novobi/novobi_calendar.xml',
        'views/pages/novobi/novobi_summary.xml',
        'views/pages/novobi/novobi_not_found.xml',

        # Data
        'data/zoom_data.xml',
        'data/finance_appointment_mail_data.xml',
        'data/novobi_appointment_mail_data.xml',
        'data/appointment_data.xml',
        'data/calendar_event_stage_data.xml',
        'data/product_template_data.xml',
        'data/service_packages_data.xml',

        # Security
        'security/ir.model.access.csv',
    ],
    'images': [],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
    'qweb': [
    ],
}
