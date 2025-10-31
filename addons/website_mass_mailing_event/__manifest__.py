{
    'name': "Mass mailing on website events",
    'summary': 'Add dynamic event snippets for the mass_mailing html builder',
    'description': """
    Add dynamic event snippets for the mass_mailing html builder, complete with links to the matching website event page.
    The snippet is linked to specified events and will automatically fetch relevant data.
    """,
    'category': 'Marketing/Email Marketing/Website',
    'depends': ['mass_mailing', 'website_event'],
    'assets': {
        'mass_mailing.assets_builder': [
            'website_mass_mailing_event/static/src/builder/**/*',
        ],
    },
    'data': [
        'views/snippets_themes.xml',
        'views/snippets/s_dynamic_snippet_event.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
