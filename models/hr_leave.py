from odoo import fields, models,_,api


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    third_approval_id = fields.Many2one('hr.employee',string='Third Approver')
    fourth_approval_id = fields.Many2one('hr.employee',string='Fourth Approver')

    state = fields.Selection(selection_add=[
        ('partial_approved', 'Partially Approved')])
    approved_by_ids = fields.Many2many('res.users', string='Approvers',tracking=True)

    can_approve = fields.Boolean(string="Can Approve", compute="_compute_can_approve", store=False)

    @api.depends('state', 'first_approver_id', 'second_approver_id', 'third_approval_id', 'fourth_approval_id',
                 'holiday_status_id')
    def _compute_can_approve(self):
        current_user = self.env.user

        for record in self:
            record.can_approve = False
            if record.state == 'confirm' and current_user == record.employee_id.leave_manager_id and not record.first_approver_id:
                record.can_approve = True
            elif record.state == 'partial_approved':
                if record.first_approver_id and not record.second_approver_id:
                    if current_user.id in record.holiday_status_id.responsible_ids.ids:
                        record.can_approve = True
                elif record.first_approver_id and record.second_approver_id and not record.third_approval_id:
                    if current_user == record.holiday_status_id.higher_authority_id:
                        record.can_approve = True
                elif record.first_approver_id and record.second_approver_id and record.third_approval_id and not record.fourth_approval_id:
                    if current_user.id in record.holiday_status_id.managing_directors_ids.ids:
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
        print("bbb")
        return True

    def activity_update(self):

        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        leave_manager_id = employee.leave_manager_id.id if employee.leave_manager_id else None
        print(leave_manager_id)
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if not holidays:
            if leave_manager_id:
                self.activity_schedule(
                    'custom_timeoff.mail_activity_timeoff',
                    user_id=leave_manager_id,
                )

    def action_approve(self):
        current_user = self.env.user
        current_employee = self.env.user.employee_id
        timeoff_bypass = self.employee_ids.department_id.timeoff_bypass
        lt = self.holiday_status_id  # leave type
        if lt.leave_validation_type == 'both' or timeoff_bypass == True:
            if not self.first_approver_id:
                if self.env.user in lt.responsible_ids:
                    print("uu")
                    self.write(
                        {'state': 'validate', 'first_approver_id': current_employee.id,'second_approver_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    self.write(
                        {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # send the mail activity for HR
                    if lt.responsible_ids:
                        for res in lt.responsible_ids:
                            self.activity_schedule(
                                'custom_timeoff.mail_activity_timeoff',
                                user_id=res.id,
                            )
                    return self.leave_approved_message()

            if self.first_approver_id and not self.second_approver_id:
                print("second")
                self.write(
                    {'state': 'validate', 'second_approver_id': current_employee.id})
                self.approved_by_ids = [(4, current_user.id)]
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.action_done()
                # Send activity for higher authority
                if lt.higher_authority_id:
                    high = lt.higher_authority_id
                    self.activity_schedule(
                        'custom_timeoff.mail_activity_timeoff',
                        user_id=high.id,
                    )
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Leave Approved',
                        'type': 'rainbow_man',
                    }
                }

        # MD Approve Case:
        elif lt.leave_validation_type == 'md':
            if not self.first_approver_id:
                if self.env.user in lt.responsible_ids:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'partial_approved', 'first_approver_id': current_employee.id,
                         'second_approver_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    if lt.higher_authority_id:
                        high = lt.higher_authority_id
                        self.activity_schedule(
                            'custom_timeoff.mail_activity_timeoff',
                            user_id=high.id,
                        )
                    return self.leave_approved_message()
                else:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                             {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                    # check the fourth approver is already approve that
                    if self.first_approver_id.user_id in lt.managing_directors_ids:
                        self.fourth_approval_id = self.first_approver_id
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # send the mail activity for HR
                    if lt.responsible_ids:
                        for res in lt.responsible_ids:
                            self.activity_schedule(
                                'custom_timeoff.mail_activity_timeoff',
                                user_id=res.id,
                            )
                    return self.leave_approved_message()
            if self.first_approver_id and not self.second_approver_id:
                self.filtered(lambda hol: hol.validation_type == 'md').write(
                    {'state': 'partial_approved', 'second_approver_id': current_employee.id})
                self.approved_by_ids = [(4, current_user.id)]
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.action_done()
                # Send activity for higher authority
                if lt.higher_authority_id:
                    high = lt.higher_authority_id
                    self.activity_schedule(
                        'custom_timeoff.mail_activity_timeoff',
                        user_id=high.id,
                    )
                return self.leave_approved_message()
            if self.first_approver_id and self.second_approver_id and not self.third_approval_id:
                if self.fourth_approval_id:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'validate', 'third_approval_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }

                else:
                    self.filtered(lambda hol: hol.validation_type == 'md').write(
                        {'state': 'partial_approved', 'third_approval_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # send notification for MD
                    if lt.managing_directors_ids:
                        for md in lt.managing_directors_ids:
                            self.activity_schedule(
                                'custom_timeoff.mail_activity_timeoff',
                                user_id=md.id,
                            )
                    return self.leave_approved_message()
            if self.first_approver_id and self.second_approver_id and self.third_approval_id and not self.fourth_approval_id:
                self.filtered(lambda hol: hol.validation_type == 'md').write(
                    {'state': 'validate', 'fourth_approval_id': current_employee.id})
                self.approved_by_ids = [(4, current_user.id)]
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.action_done()
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Leave Approved',
                        'type': 'rainbow_man',
                    }
                }

        elif lt.leave_validation_type == 'higher':
            if not self.first_approver_id:
                if self.env.user in lt.responsible_ids:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'partial_approved', 'first_approver_id': current_employee.id,'second_approver_id': current_employee.id })
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # send the mail activity for HR
                    if lt.higher_authority_id:
                        for res in lt.higher_authority_id:
                            self.activity_schedule(
                                'custom_timeoff.mail_activity_timeoff',
                                user_id=res.id,
                            )
                    return self.leave_approved_message()
                else:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'partial_approved', 'first_approver_id': current_employee.id})
                    if self.first_approver_id.user_id in lt.higher_authority_id:
                        self.third_approval_id = self.first_approver_id
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # send the mail activity for HR
                    if lt.responsible_ids:
                        for res in lt.responsible_ids:
                            self.activity_schedule(
                                'custom_timeoff.mail_activity_timeoff',
                                user_id=res.id,
                            )
                    return self.leave_approved_message()


            if self.first_approver_id and not self.second_approver_id:
                if self.third_approval_id:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'validate', 'second_approver_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'Leave Approved',
                            'type': 'rainbow_man',
                        }
                    }
                else:
                    self.filtered(lambda hol: hol.validation_type == 'higher').write(
                        {'state': 'partial_approved', 'second_approver_id': current_employee.id})
                    self.approved_by_ids = [(4, current_user.id)]
                    activity_ids = self.activity_ids
                    if activity_ids:
                        activity_ids.action_done()
                    # Send activity for higher authority
                    if lt.higher_authority_id:
                        high = lt.higher_authority_id
                        self.activity_schedule(
                            'custom_timeoff.mail_activity_timeoff',
                            user_id=high.id,
                        )
                    return self.leave_approved_message()

            if self.first_approver_id and self.second_approver_id and not self.third_approval_id:
                self.filtered(lambda hol: hol.validation_type == 'higher').write(
                    {'state': 'validate', 'third_approval_id': current_employee.id})
                self.approved_by_ids = [(4, current_user.id)]
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.action_done()
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Leave Approved',
                        'type': 'rainbow_man',
                    }
                }
        else:
            self.sudo().action_validate()

    @api.onchange('request_date_from','request_date_to','number_of_days_display')
    def _onchange_bt(self):

        if not self.request_unit_half:
            self.holiday_status_id = ''



