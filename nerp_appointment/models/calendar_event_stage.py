# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import fields, api, models


class CalendarEventStage(models.Model):
    _name = "calendar.event.stage"
    _description = "Calendar Event Stage"
    _order = 'sequence'

    #########
    # FIELDS
    #########
    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Open'),
         ('closed', 'Closed')],
        string='State',
        default='new',
    )
