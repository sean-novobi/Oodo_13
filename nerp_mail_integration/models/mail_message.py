
from odoo import _, api, fields, models, modules, tools

class Message(models.Model):
    _inherit = 'mail.message'
    send_to = fields.Char(string='Send To')

