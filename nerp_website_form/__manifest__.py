# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################

{
    'name': 'NERP: Website Form',
    'version': '1.0',
    'website': 'https://www.novobi.com',
    'category': '',
    'author': 'Novobi LLC',
    'depends': [
        'base', 'website', 'website_form', 'nerp_recaptcha'
    ],
    'description': """
=======================
NOVOBI Trial - Frontend
=======================

This module is designed and developed in order to extend Website Form
""",
    'data': [
        'views/website_form_templates.xml'
    ],
    'images': [],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
    'qweb': [
    ],
}
