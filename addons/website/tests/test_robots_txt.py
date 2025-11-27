from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestRobotsTxt(HttpCase):
    def setUp(self):
        super().setUp()
        self.website = self.env['website'].get_current_website()
        self.Attachment = self.env['ir.attachment'].sudo()

    def test_website_install_uninstall(self):
        """
        Test that robots.txt is created on website install and removed on
        uninstall from attachment.
        """
        self.url_open('/robots.txt')
        attachment = self.Attachment.search([
            ('name', '=', 'robots.txt'),
            ('website_id', '=', self.website.id),
        ])
        self.assertTrue(attachment)

        self.env['ir.module.module'].search([
            ('name', '=', 'website')
        ]).state = 'to remove'
        attachment = self.Attachment.search([
            ('name', '=', 'robots.txt'),
            ('website_id', '=', self.website.id),
        ])
        self.assertFalse(attachment)

    def test_update_on_user_rules(self):
        """Test that robots.txt is updated when modified with user rules."""
        self.website.write({
            'robots_txt': 'Disallow: /test_settings'
        })

        attachment = self.Attachment.search([
            ('name', '=', 'robots.txt'),
            ('website_id', '=', self.website.id),
        ])
        self.assertIn('Disallow: /test_settings', attachment.index_content)

    def test_website_dependent_module_install_uninstall(self):
        """Test that robots.txt is updated when a website-dependent module
        is installed or uninstalled.
        """
        self.url_open("/robots.txt")

        dummy_module = self.env["ir.module.module"].create({
            "name": "test_dependent_module",
            "state": "uninstalled",
        })
        self.env["ir.module.module.dependency"].create({
            "module_id": dummy_module.id,
            "name": "website",
        })

        self.env["ir.module.module"].search([
            ("name", "=", "website_blog")
        ]).state = "to install"
        # assert if robots.txt is uptaed and our assertion string is INCLUDED in the attacmet
        self.env["ir.module.module"].search([
            ("name", "=", "website_blog")
        ]).state = "to remove"
        # assert if robots.txt is uptaed and our assertion string is EXCLUDED in the attacmet
