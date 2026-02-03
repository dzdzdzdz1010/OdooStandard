from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


class TestWebsiteEventSale(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):

    def test_website_event_sale_free_tickets(self):
        """ Test saleorder is not created for tickets free tickets """
        self.authenticate(None, None)
        free_ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'Free',
            'product_id': self.product_event.id,
            'price': 0,
        })
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        existing_so = self.env['sale.order'].search([])
        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertEqual(self.env['sale.order'].search([]), existing_so, "Sale order should not be created for the free tickets")
        self.assertEqual(len(self.event.registration_ids), event_registration_count + 1)

    def test_website_event_sale_free_paid_mix(self):
        """ Test saleorder is created if paid ticket selected """
        self.authenticate(None, None)
        free_ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'Free',
            'product_id': self.product_event.id,
            'price': 0,
        })
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': self.ticket.id,
            f'2-name-{name_question.id}': 'joe',
            f'2-email-{email_question.id}': 'joe@test.lan',
            f'2-phone-{phone_question.id}': '8989898988',
            '2-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })

        self.assertEqual(len(self.event.registration_ids), event_registration_count + 2)
        self.assertTrue(self.env['sale.order'].search([
            ('order_line.event_ticket_id', '=', self.ticket.id),
            ('order_line.event_ticket_id', '=', free_ticket.id)
        ]), "Sale order should be created for the free/paid tickets mix")

    def test_website_event_registration_redirection_for_public_user_with_no_address(self):
        """ Public users with no existing billing address registering for an event
        which requires payment should be redirected to the billing address form. """
        self.authenticate(None, None)
        ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'New Ticket',
            'product_id': self.product_event.id,
            'price': 10,
        })
        event_questions = self.event.question_ids
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        registration_data = {
            f'1-name-{name_question.id}': 'New Public Customer',
            f'1-email-{email_question.id}': 'new_public_customer@test.example.com',
            f'1-phone-{phone_question.id}': '123456789',
            '1-event_ticket_id': ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        }
        url = f'/event/{self.event.id}/registration/confirm'
        response = self.url_open(url, data=registration_data, allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        new_partner = self.env['res.partner'].search([
            ('name', '=', 'New Public Customer'),
            ('type', '=', 'invoice'),
        ])
        self.assertIn(f'/shop/address?partner_id={new_partner.id}&address_type=billing', response.url)
