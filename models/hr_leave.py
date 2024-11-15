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

    def action_confirm(self):
        self.write({'state': 'confirm'})
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if holidays:
            # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
            holidays.sudo().action_validate()
        self.activity_update()
        return True

    def activity_update(self):
        print("activity workded")
        holiday_status_id = self.holiday_status_id
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        parent_user_id = employee.parent_id.user_id.id if employee.parent_id else None
        print(parent_user_id)
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if not holidays:
            if parent_user_id:
                self.activity_schedule(
                    'custom_timeoff.mail_activity_timeoff',
                    user_id=parent_user_id,
                )
            if holiday_status_id.responsible_ids:
                for res in holiday_status_id.responsible_ids:
                    self.activity_schedule(
                        'custom_timeoff.mail_activity_timeoff',
                        user_id=res.id,
                    )
            if holiday_status_id.higher_authority_id:
                high = holiday_status_id.higher_authority_id
                self.activity_schedule(
                    'custom_timeoff.mail_activity_timeoff',
                    user_id=high.id,
                )
            if holiday_status_id.managing_directors_ids:
                for md in holiday_status_id.managing_directors_ids:
                    self.activity_schedule(
                        'custom_timeoff.mail_activity_timeoff',
                        user_id=md.id,
                    )

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
                print(lt.responsible_ids.ids)
                if self.first_approver_id:
                    print("turee")
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
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.unlink()
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }
            else:
                raise UserError(_('Not Approved from the lower level'))

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
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.unlink()
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


