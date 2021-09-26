# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import fields, models, api
import logging

class ResPartner(models.Model):
    _inherit = "res.partner"

    ##########
    # HELPER
    ##########

    @api.model
    def get_partner(self, partner_info):
        fname = partner_info.get('fname', False)
        lname = partner_info.get('lname', False)
        name = partner_info.get('name', False)
        email = partner_info.get('email')
        phone = partner_info.get('phone', False)
        company_name = partner_info.get('company_name', False)

        country_id = self.env.ref('base.us').id
        if not email:
            return None

        partner_id = self.env['res.partner'].sudo().search([('email', '=ilike', email),
                                                            ('is_company', '=', False)], limit=1)

        if not partner_id:
            if fname or lname:
                partner_id = partner_id.sudo().create({
                    'name': fname + ' ' + lname,
                    'email': email,
                })
            elif name:
                partner_id = partner_id.sudo().create({
                    'name': name,
                    'email': email,
                })
            else:
                partner_id = partner_id.sudo().create({
                    'name': email.split('@')[0],
                    'email': email,
                })

        if phone:
            partner_id.sudo().write({'phone': phone})

        if company_name:
            company_id = self.env['res.partner'].sudo().search([('name', '=ilike', company_name),
                                                                ('is_company', '=', True)], limit=1)
            if company_id:
                partner_id.sudo().write({'parent_id': company_id.id})
            else:
                parent = self.env['res.partner'].create({'name': company_name, 'is_company': True})
                partner_id.sudo().write({
                    'parent_id': parent.id
                })
        if not partner_id.country_id:
            partner_id.country_id = country_id
        if partner_id.parent_id and not partner_id.parent_id.country_id:
            partner_id.parent_id.country_id = country_id
        return partner_id

