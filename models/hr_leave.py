from odoo import fields, models,_,api
from odoo.exceptions import UserError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    third_approval_id = fields.Many2one('res.users',string='Third Approver')
    fourth_approval_id = fields.Many2one('res.users',string='Fourth Approver')
    leave_approved_by_ids = fields.Many2many('res.users',string='Approved By')

    state = fields.Selection(selection_add=[
        ('partial_approved', 'Partially Approved')])

    can_approve = fields.Boolean(string="Can Approve", compute="_compute_can_approve", store=False)

    @api.depends('state', 'leave_approved_by_ids', 'first_approver_id', 'second_approver_id', 'third_approval_id',
                 'fourth_approval_id')
    def _compute_can_approve(self):
        """
        Determine if the current user can approve the leave request.
        """
        for record in self:
            # Reset visibility
            record.can_approve = False
            current_user = self.env.user

            if record.state == 'confirm':
                # First approver can approve if they haven't approved yet
                if current_user == record.employee_id.leave_manager_id and current_user not in record.leave_approved_by_ids:
                    record.can_approve = True

            elif record.state == 'partial_approved':
                # Second approver's turn
                if not record.first_approver_id:
                    continue  # Skip if the first approver hasn't approved yet

                if current_user.id in record.holiday_status_id.responsible_ids.ids and current_user not in record.leave_approved_by_ids:
                    record.can_approve = True

                # Third approver's turn
                elif record.first_approver_id and record.second_approver_id and current_user == record.holiday_status_id.higher_authority_id:
                    if current_user not in record.leave_approved_by_ids:
                        record.can_approve = True

                # Fourth approver's turn
                elif (
                        record.first_approver_id
                        and record.second_approver_id
                        and record.third_approval_id
                        and current_user.id in record.holiday_status_id.managing_directors_ids.ids
                ):
                    if current_user not in record.leave_approved_by_ids:
                        record.can_approve = True

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

    def action_approve(self):
        current_employee = self.env.user.employee_id
        print(current_employee.id)
        current_user = self.env.user
        # current leave - leave type
        lt = self.holiday_status_id  # leave type
        if lt.leave_validation_type == 'both':
            if current_user == self.employee_id.leave_manager_id:
                self.filtered(lambda hol: hol.validation_type == 'both').write(
                    {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                self.leave_approved_by_ids = [(4,current_user.id)]
                return self.leave_approved_message()

            if current_user.id in lt.responsible_ids.ids:
                if self.first_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'both').write(
                        {'state': 'validate', 'second_approver_id': current_employee.id})
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

        # MD Approve Case:
        elif lt.leave_validation_type == 'md':
            if current_user == self.employee_id.leave_manager_id:
                self.filtered(lambda hol: hol.validation_type == 'md').write(
                    {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                self.leave_approved_by_ids = [(4,current_user.id)]
                return self.leave_approved_message()

            if current_user.id in lt.responsible_ids.ids:
                print(lt.responsible_ids.ids)
                if self.first_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'partial_approved', 'second_approver_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()

            if current_user  == lt.higher_authority_id:
                if self.first_approver_id and self.second_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'partial_approved', 'third_approval_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()

            if current_user.id in lt.managing_directors_ids.ids:
                if self.first_approver_id and self.second_approver_id and self.third_approval_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'validate', 'fourth_approval_id': current_employee.id})
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
            print("yess")
            if current_user == self.employee_id.leave_manager_id:
                print("1st")
                self.filtered(lambda hol: hol.validation_type == 'higher').write(
                    {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                self.leave_approved_by_ids = [(4, current_user.id)]
                return self.leave_approved_message()

            if current_user.id in lt.responsible_ids.ids:
                print("2st")
                if self.first_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'partial_approved', 'second_approver_id': current_employee.id})
                    self.leave_approved_by_ids = [(4, current_user.id)]
                    return self.leave_approved_message()

            if current_user  == lt.higher_authority_id:
                print("3st")
                if self.first_approver_id and self.second_approver_id:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'validate', 'third_approval_id': current_employee.id})
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
                raise UserError(_('Other Approvers are not Approved '))

        else:
            self.sudo().action_validate()


