from odoo import fields,models

class HrDepartmentInherit(models.Model):
    _inherit = 'hr.department'

    timeoff_bypass = fields.Boolean(string='Timeoff approval Bypass',default=False)