from odoo import models,fields


class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    related_joinee = fields.Many2one(
        'employee.joining.form',
        string="Related Joinee",
        groups="custom_timeoff.group_read_specific_fields")
    agent_number = fields.Char(string="Agent Number",groups="your_module_name.group_read_specific_fields")