from odoo import fields, models,_,api
from odoo.exceptions import UserError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    third_approval_id = fields.Many2one('res.users',string='Third Approver')
    fourth_approval_id = fields.Many2one('res.users',string='Fourth Approver')
    leave_approved_by_ids = fields.Many2many('res.users',string='Approved By')

    def leave_approved_message(self):
        """Reusable function to show the 'Leave Approved' rainbow message effect."""
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Your Approved'),  # `_` for translation support
                'type': 'rainbow_man',
            }
        }
    def onchange(self,values,field_names,fields_spec):
        """  this for leave type set"""
        print("hello")

        return super().onchange(values, field_names, fields_spec)

    def action_approve(self, check_state=True):
        if check_state and any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))
        self.write({'state': 'confirm'})

        # fetch current user employee_id
        current_employee = self.env.user.employee_id
        print(current_employee.id)
        current_user = self.env.user
        # current leave - leave type
        lt = self.holiday_status_id

        # MD Approve Case:
        if lt.leave_validation_type == 'md':
            if current_user == self.employee_id.leave_manager_id:
                self.filtered(lambda hol: hol.validation_type == 'md').write(
                    {'state': 'confirm', 'first_approver_id': current_employee.id})
                self.leave_approved_by_ids = [(4,current_user.id)]
                return self.leave_approved_message()

            if current_user.id in lt.responsible_ids.ids:
                if self.first_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'confirm', 'second_approver_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()

            if current_user  == lt.higher_authority_id:
                if self.first_approver_id and self.second_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'confirm', 'third_approval_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()

            if current_user.id in lt.managing_directors_ids.ids:
                if self.first_approver_id and self.second_approver_id and self.third_approval_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'validate1', 'fourth_approval_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }

        # higher authority approve:
        elif lt.leave_validation_type == 'higher':
            if current_user == self.employee_id.leave_manager_id:
                self.filtered(lambda hol: hol.validation_type == 'higher').write(
                    {'state': 'confirm', 'first_approver_id': current_employee.id})
                self.leave_approved_by_ids = [(4, current_user.id)]
                return self.leave_approved_message()
            if current_user.id in lt.responsible_ids.ids:
                if self.first_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'confirm', 'second_approver_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()
            if current_user  == lt.higher_authority_id:
                if self.first_approver_id and self.second_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'validate1', 'third_approval_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    raise UserError(_('Other Approvers are not Approved '))

        else:
            self.sudo().action_validate()


