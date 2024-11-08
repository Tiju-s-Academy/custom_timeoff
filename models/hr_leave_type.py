from odoo import models, fields


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type',

    leave_validation_type = fields.Selection(selection_add=[('higher',
                                                             "By Employee's Approver and Time Off Officer"
                                                             " and Higher Person"),
                                                            ('md',
                                                             "By Employee's Approver and Time Off Officer and Higher"
                                                             " Person and Managing Director")])
    higher_authority_id = fields.Many2one('res.users', string='Higher Authority Officer',
                                          help="Choose the Higher Authorities who will be notified to approve"
                                               " allocation or Time Off Request. If empty, nobody will be notified")
    managing_directors_ids = fields.Many2many('res.users', 'director_users', string='Managing Directors',
                                              help="Choose the Managing Directors who will be notified to approve"
                                                   " allocation or Time Off Request. If empty, nobody will be notified")
