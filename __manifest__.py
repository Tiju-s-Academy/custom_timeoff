{
    'name': 'custom timeoff',
    'version': '17.0.1.0.0',
    'summary': 'add new type approvers',
    'depends': ['base','web','mail','hr_holidays','hr'],
    'data': [
        'security/groups.xml',
        'security/record_rule.xml',
        'views/hr_leave_type_inherit_view.xml',
        'views/hr_leave_view_inherit.xml',
    ],
    'application' : False,
    'license': 'LGPL-3',
}