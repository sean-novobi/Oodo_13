# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
import logging


class ServicePackages(models.Model):
    _name = "service.packages"
    _description = "Map Service Packages and Products"

    name = fields.Char(string='Service Name')
    quantity = fields.Integer(string='Package Quantity', help='Number of product qty which will be added to Sale Order Line', default=1)
    price = fields.Float(string='Price', default=1.0, digits="Product Price", help='Price of total packages which will be showed on website and will be used to calculate the discount line')
    product_template_id = fields.Many2one('product.template', string='Product Template', help='Product which will be used to add to Sale Order Line')
    package_type = fields.Selection([
        ('finance_appointment', 'Finance Support Session'),
    ], string="Package Type", help="Type of Packages in case we have multiple types in future")
    description = fields.Char(string='Website Description', help='Description of the package which will be showed on website')
    discount_tag = fields.Selection(selection=[('10', '10% Savings'),
                                               ('20', '20% Savings')], string='Discount Tag')

    def get_support_session_service(self, quantity, package_type=None):
        domain = [('quantity','=',quantity)]
        if package_type:
            domain += [('package_type', '=', package_type)]
        return self.env['service.packages'].sudo().search(domain, limit=1)

