# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import api, fields, models


class Employee(models.Model):
    _inherit = 'hr.employee'

    ##########
    # FIELDS
    ##########
    zoom_api_key = fields.Char('Zoom API Key', config_parameter='zoom._api_key',
                               help='API Key from Novobi Zoom Marketplace App')
    zoom_api_secret = fields.Char('Zoom API Secret', config_parameter='zoom._api_secret',
                                  help='API Secret from Novobi Zoom Marketplace App')
    zoom_email = fields.Char('Zoom User Email', config_parameter='zoom._email',
                             help='User Email which will be used to create meeting rooms')

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    zoom_api_key = fields.Char('Zoom API Key', config_parameter='zoom._api_key',
                               help='API Key from Novobi Zoom Marketplace App')
    zoom_api_secret = fields.Char('Zoom API Secret', config_parameter='zoom._api_secret',
                                  help='API Secret from Novobi Zoom Marketplace App')
    zoom_email = fields.Char('Zoom User Email', config_parameter='zoom._email',
                             help='User Email which will be used to create meeting rooms')