{
    'name': 'Portal HR Applicant Kanban Demo',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Embed backend applicant kanban in the customer portal.',
    'depends': [
        'hr_recruitment',
        'portal',
        'web',
    ],
    'data': [
        'views/portal_project_sharing_templates.xml',
        'views/portal_project_sharing_actions.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
