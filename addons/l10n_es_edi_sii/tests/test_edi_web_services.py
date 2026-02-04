# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.tests import tagged
from odoo import fields
from .common import TestEsEdiCommon
from unittest.mock import patch


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiWebServices(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Invoice name are tracked by the web-services so this constant tries to get a new unique invoice name at each
        # execution.
        cls.today = datetime.now()
        cls.time_name = cls.today.strftime('%H%M%S')

        cls.out_invoice = cls.env['account.move'].create({
            'name': f'INV{cls.time_name}',
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })
        cls.out_invoice.action_post()

        cls.in_invoice = cls.env['account.move'].create({
            'name': f'BILL{cls.time_name}',
            'ref': f'REFBILL{cls.time_name}',
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': fields.Date.to_string(cls.today.date()),
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('p_iva10_bc').ids)],
            })],
        })
        cls.in_invoice.action_post()

        cls.moves = cls.out_invoice + cls.in_invoice

    @patch(
        'odoo.addons.l10n_es_edi_sii.models.sii_service.L10nEsSiiService._l10n_es_edi_call_web_service_sign',
        side_effect=lambda invoice, info_list, **kwargs: {invoice: {'success': True}},
    )
    def test_edi_gipuzkoa(self, _mock):
        self.env.company.l10n_es_sii_tax_agency = 'gipuzkoa'
        self.env['l10n_es.sii.service']._send_sii_invoice(self.out_invoice)
        self.env['l10n_es.sii.service']._send_sii_invoice(self.in_invoice)

        self.assertRecordValues(self.out_invoice, [
            {'l10n_es_edi_sii_state': 'sent'}
        ])
        self.assertRecordValues(self.in_invoice, [
            {'l10n_es_edi_sii_state': 'sent'}
        ])

    @patch(
        'odoo.addons.l10n_es_edi_sii.models.sii_service.L10nEsSiiService._l10n_es_edi_call_web_service_sign',
        side_effect=lambda invoice, info_list, **kwargs: {invoice: {'success': True}},
    )
    def test_edi_bizkaia(self, _mock):
        self.env.company.l10n_es_sii_tax_agency = 'bizkaia'

        self.env['l10n_es.sii.service']._send_sii_invoice(self.out_invoice)
        self.env['l10n_es.sii.service']._send_sii_invoice(self.in_invoice)

        self.assertRecordValues(self.out_invoice, [
            {'l10n_es_edi_sii_state': 'sent'}
        ])
        self.assertRecordValues(self.in_invoice, [
            {'l10n_es_edi_sii_state': 'sent'}
        ])
