{
    'name': 'custom timeoff',
    'version': '17.0.2.0.0',
    'summary': 'add new type approvers',
    'depends': ['base','web','mail','hr_holidays'],
    'data': [
        'views/hr_leave_type_inherit_view.xml',
        'views/hr_leave_view_inherit.xml',
        'views/hr_department_view.xml',
    ],
    'application' : False,
    'license': 'LGPL-3',
}