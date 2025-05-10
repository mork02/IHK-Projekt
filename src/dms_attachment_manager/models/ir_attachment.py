from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    is_exported = fields.Boolean(string="Exported", default=False)
