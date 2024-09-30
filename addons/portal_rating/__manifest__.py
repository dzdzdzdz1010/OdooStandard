# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal Rating',
    'category': 'Services',
    'description': """
Bridge module adding rating capabilities on portal. It includes notably
inclusion of rating directly within the customer portal discuss widget.
        """,
    'depends': [
        'portal',
        'rating',
    ],
    'data': [
        'views/rating_rating_views.xml',
        'views/portal_templates.xml',
        'views/rating_templates.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'portal_rating/static/src/scss/portal_rating.scss',
            'portal_rating/static/src/xml/portal_chatter.xml',
            'portal_rating/static/src/interactions/**/*',
            'portal_rating/static/src/xml/portal_rating_composer.xml',
            'portal_rating/static/src/xml/portal_tools.xml',
            # The field definitions are processed once when the page loads. This part is necessary
            # for fields that may be used when a common scope is lazily loaded in the frontend.
            'portal_rating/static/src/core/common_frontend/**/*',
        ],
        'web.assets_unit_tests_setup': [
            'portal_rating/static/src/interactions/**/*',
            'portal_rating/static/src/xml/**/*',
        ],
        'portal.assets_chatter': [
            'portal_rating/static/src/chatter/portal/**/*',
        ],
        'portal.assets_chatter_style': [
            'portal_rating/static/src/scss/portal_rating.scss',
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
