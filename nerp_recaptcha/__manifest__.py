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
    'name': 'NERP: Recaptcha',
    'version': '1.0',
    'website': 'https://www.novobi.com',
    'category': '',
    'author': 'Novobi LLC',
    'depends': [
        'base', 'website'
    ],
    'description': """
=======================
NOVOBI Trial - Frontend
=======================

This module is designed and developed in order to integrate Google Recaptcha with Odoo
""",
    'data': [
        'views/assets.xml',
        'data/recaptchav3_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': [],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
    'qweb': [
    ],
}
