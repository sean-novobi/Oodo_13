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
    'name': 'NERP: General Setting',
    'version': '1.0',
    'website': 'https://www.novobi.com',
    'category': '',
    'author': 'Novobi LLC',
    'depends': [
        'base', 'mail', 'website'
    ],
    'description': """
=======================
NOVOBI General Setting
=======================

This module is developed for general setup in NERP project, such as: Outgoing/Incoming Mail Server supports multi companies
""",
    'data': [
        # 'data/portal_data.xml',
        'views/res_company_views.xml',
        'views/mail_alias_views.xml',
        'views/mail_blacklist_domain_views.xml',
        'views/mail_blacklist_mail_views.xml',
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
