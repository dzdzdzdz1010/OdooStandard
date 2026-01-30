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

    def test_website_event_sale_giftcard_covers_full_cost(self):
        """Test saleorder is not auto confirmed if the gift card in the card can fully cover the cost"""
        self.authenticate(None, None)
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
            'csrf_token': http.Request.csrf_token(self),
        })

        gift_card = self.env['loyalty.card'].create({
            'program_id': self.env.ref('loyalty.gift_card_program').id,
            'points': 200.0,
        })

        self.url_open('/shop/pricelist', data={
            'promo': gift_card.code,
            'csrf_token': http.Request.csrf_token(self),
            })

        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': self.ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        last_so = self.env['sale.order'].search([], order='id desc', limit=1)
        self.assertEqual(len(self.event.registration_ids), event_registration_count + 2)
        self.assertTrue(last_so.state == 'draft', "The status of upaid events should be draft")
