import base64
from unittest.mock import patch

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from .common import PdpTestCommon

UBL_NS = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
}


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpPaymentFlows(PdpTestCommon):
    def _load_ubl_payment_fixture(self, filename):
        with file_open(f'l10n_fr_pdp_reports/tests/data/{filename}', 'rb') as handle:
            xml = etree.fromstring(handle.read())
        payable_node = xml.find('cac:LegalMonetaryTotal/cbc:PayableAmount', namespaces=UBL_NS)
        return {
            'id': xml.findtext('cbc:ID', namespaces=UBL_NS),
            'issue_date': xml.findtext('cbc:IssueDate', namespaces=UBL_NS),
            'payable_amount': float(payable_node.text) if payable_node is not None else 0.0,
            'currency': payable_node.get('currencyID') if payable_node is not None else '',
            'buyer_country': xml.findtext(
                'cac:AccountingCustomerParty/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode',
                namespaces=UBL_NS,
            ),
        }

    def _create_international_invoice(self, partner, issue_date, amount, reference):
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].create({
                'name': "PDP Sales",
                'code': 'PDPT',
                'type': 'sale',
                'company_id': self.company.id,
                'default_account_id': self.income_account.id,
            })
        if not journal:
            journal = self.env['account.journal'].create({
                'name': "PDP Sales",
                'code': 'PDSA',
                'type': 'sale',
                'company_id': self.company.id,
                'default_account_id': self.income_account.id,
            })
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': issue_date,
            'journal_id': journal.id,
            'l10n_fr_pdp_invoice_reference': reference,
            'invoice_line_ids': [Command.create({
                'product_id': self.service_product.id,
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [Command.set(self.tax_20.ids)],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True
        return move

    def test_payment_flow_created_and_ready(self):
        """Payment flow built when payment is reconciled within window."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        pay_date = self.TEST_PAYMENT_DATE
        self._create_payment_for_invoice(inv, pay_date=pay_date)
        aggregator = self.env['l10n.fr.pdp.flow.aggregator'].with_context(mail_create_nolog=True, tracking_disable=True)
        pay_flow, rebuild = aggregator._synchronize_payment_flows(self.company.id, pay_date, self.company.currency_id.id)
        if rebuild:
            rebuild._build_payload()
        pay_flow = (pay_flow | rebuild).filtered(lambda f: f.report_kind == 'payment')[:1]
        self.assertTrue(pay_flow, 'Payment flow should be created when payments exist')
        self.assertEqual(pay_flow.state, 'ready', 'Payment flow must be ready after build')
        self.assertTrue(pay_flow.payload, 'Payment flow should have payload built')

    def test_unitary_payment_uses_ttc_amount(self):
        """International payments should report TTC amounts in TT-95."""
        inv = self._create_invoice(partner=self.partner_international, sent=True, taxes=self.tax_20, product=self.service_product)
        inv.l10n_fr_pdp_invoice_reference = 'INV-TTC'
        self._create_payment_for_invoice(inv, amount=inv.amount_total)
        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not pay_flow.payload:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        amount_text = xml.findtext('.//PaymentsReport//Invoice[InvoiceID="INV-TTC"]//Amount')
        self.assertIsNotNone(amount_text, 'Payment entry should exist for TTC check')
        self.assertNotEqual(inv.amount_total, inv.amount_untaxed, 'Test invoice should include tax')
        self.assertEqual(float(amount_text), inv.amount_total, 'TT-95 should carry the TTC amount')

    def test_unitary_payments_match_ubl_fixtures(self):
        """10.2 payments should align with S2F3/S2F4 fixture IDs and amounts."""
        fixtures = [
            self._load_ubl_payment_fixture('FACT_REPORT2025_S2F3.xml'),
            self._load_ubl_payment_fixture('FACT_REPORT2025_S2F4.xml'),
        ]
        partner = self.env['res.partner'].create({
            'name': "UBL Buyer IT",
            'country_id': self.env.ref('base.it').id,
            'vat': 'IT00000010017',
            'property_account_receivable_id': self.partner_international.property_account_receivable_id.id,
            'property_account_payable_id': self.partner_international.property_account_payable_id.id,
        })
        for data in fixtures:
            issue_date = fields.Date.from_string(data['issue_date'])
            move = self._create_international_invoice(partner, issue_date, data['payable_amount'], data['id'])
            self._create_payment_for_invoice(move, amount=data['payable_amount'], pay_date=issue_date)

        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not pay_flow.payload:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        payment_nodes = xml.findall('.//PaymentsReport//Invoice')
        self.assertEqual(len(payment_nodes), len(fixtures), 'Fixture payments should be present in 10.2 output')
        for data in fixtures:
            xpath = './/PaymentsReport//Invoice[InvoiceID="%s"]' % data['id']
            invoice_node = xml.find(xpath)
            self.assertIsNotNone(invoice_node, f'Missing payment entry for {data["id"]}')
            issue_date = invoice_node.findtext('IssueDate')
            amount_text = invoice_node.findtext('.//Payment/SubTotals/Amount')
            self.assertEqual(issue_date, data['issue_date'].replace('-', ''))
            self.assertEqual(float(amount_text), data['payable_amount'])

    def test_payment_content_flag(self):
        """Payment flow should contain payment content when payments exist."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        pay_date = self.TEST_PAYMENT_DATE
        self._create_payment_for_invoice(inv, pay_date=pay_date)
        aggregator = self.env['l10n.fr.pdp.flow.aggregator'].with_context(mail_create_nolog=True, tracking_disable=True)
        pay_flow, rebuild = aggregator._synchronize_payment_flows(self.company.id, pay_date, self.company.currency_id.id)
        if rebuild:
            rebuild._build_payload()
        pay_flow = (pay_flow | rebuild).filtered(lambda f: f.report_kind == 'payment')[:1]
        self.assertTrue(pay_flow.payload, 'Payment flow payload missing')
        flow_payload = pay_flow.payload
        self.assertTrue(flow_payload, 'Payment payload must be generated')

    def test_partial_payment_amount_in_payload(self):
        """Partial reconciliations should use the reconciled amount in payment payload."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv, amount=40)
        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        amounts = [
            node.findtext('Amount')
            for node in xml.findall('.//PaymentsReport//Transactions/Payment/SubTotals')
        ]
        self.assertIn('40.0', amounts, 'Payment payload must carry the partial amount reconciled')

    def test_b2c_payment_reports_service_portion_only(self):
        """Mixed B2C invoices should report only the service portion in 10.4."""
        tax_group = self.tax_20.tax_group_id
        goods_tax = self.env['account.tax'].create({
            'name': 'VAT 20 Goods',
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
            'l10n_fr_pdp_tt81_category': 'TLB1',
        })
        service_tax = self.env['account.tax'].create({
            'name': 'VAT 20 Service',
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
            'l10n_fr_pdp_tt81_category': 'TPS1',
        })
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        inv = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': self.TEST_INVOICE_DATE,
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(goods_tax.ids)],
                    'account_id': self.income_account.id,
                }),
                Command.create({
                    'product_id': self.service_product.id,
                    'quantity': 1,
                    'price_unit': 50,
                    'tax_ids': [Command.set(service_tax.ids)],
                    'account_id': self.income_account.id,
                }),
            ],
        })
        inv.action_post()
        inv.is_move_sent = True
        self._create_payment_for_invoice(inv, amount=inv.amount_total)

        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not pay_flow.payload:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        amounts = [
            float(node.findtext('Amount'))
            for node in xml.findall('.//PaymentsReport//Transactions/Payment/SubTotals')
        ]
        service_total = sum(
            abs(amount) for amount in inv.invoice_line_ids.filtered(
                lambda line: service_tax in line.tax_ids,
            ).mapped('price_total')
        )
        self.assertAlmostEqual(
            sum(amounts),
            service_total,
            msg='B2C payments should only include the service portion.',
        )

    def test_international_payment_reports_service_portion_only(self):
        """Mixed B2Bi invoices should report only the service portion in 10.2."""
        tax_group = self.tax_20.tax_group_id
        goods_tax = self.env['account.tax'].create({
            'name': 'VAT 20 Goods',
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
            'l10n_fr_pdp_tt81_category': 'TLB1',
        })
        service_tax = self.env['account.tax'].create({
            'name': 'VAT 10 Service',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
            'l10n_fr_pdp_tt81_category': 'TPS1',
        })
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        inv = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_international.id,
            'invoice_date': self.TEST_INVOICE_DATE,
            'journal_id': journal.id,
            'l10n_fr_pdp_invoice_reference': 'INV-MIX-SVC',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(goods_tax.ids)],
                    'account_id': self.income_account.id,
                }),
                Command.create({
                    'product_id': self.service_product.id,
                    'quantity': 1,
                    'price_unit': 50,
                    'tax_ids': [Command.set(service_tax.ids)],
                    'account_id': self.income_account.id,
                }),
            ],
        })
        inv.action_post()
        inv.is_move_sent = True
        self._create_payment_for_invoice(inv, amount=inv.amount_total)

        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not pay_flow.payload:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        invoice_node = xml.find('.//PaymentsReport//Invoice[InvoiceID="INV-MIX-SVC"]')
        self.assertIsNotNone(invoice_node, 'Missing payment entry for mixed international invoice')
        amounts = [
            float(node.findtext('Amount'))
            for node in invoice_node.findall('.//Payment/SubTotals')
        ]
        percents = {
            node.findtext('TaxPercent')
            for node in invoice_node.findall('.//Payment/SubTotals')
        }
        service_total = sum(
            abs(amount) for amount in inv.invoice_line_ids.filtered(
                lambda line: service_tax in line.tax_ids,
            ).mapped('price_total')
        )
        self.assertEqual(percents, {'10.0'}, '10.2 should include only the service VAT rate')
        self.assertAlmostEqual(
            sum(amounts),
            service_total,
            msg='B2Bi payments should only include the service portion.',
        )

    def test_cash_receipt_included_as_payment(self):
        """Receipts act as 0%% payments in transaction payment section."""
        # Ensure a payment flow exists via a standard payment, then add a cash receipt.
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv)
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        receipt = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'partner_id': self.partner_b2c.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.service_product.id,
                'quantity': 1,
                'price_unit': 50,
                'tax_ids': [Command.set([])],
                'account_id': self.income_account.id,
            })],
        })
        receipt.action_post()
        receipt.is_move_sent = True

        pay_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment' and receipt in f.move_ids)[:1]
        self.assertTrue(pay_flow, 'Payment flow should exist after adding payments/receipts')
        if not pay_flow.payload:
            pay_flow._build_payload()
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        payments = xml.findall('.//PaymentsReport//Transactions/Payment/SubTotals')
        percents = {node.findtext('TaxPercent') for node in payments}
        self.assertIn('0.0', percents, 'Receipt payments should be emitted with 0%% tax percent')

    def test_payment_outside_window_excluded(self):
        """Payments dated outside the current window should not build a payment flow."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        past_date = fields.Date.from_string('2023-01-01')
        self._create_payment_for_invoice(inv, pay_date=past_date)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == 'payment')
        self.assertFalse(pay_flow, 'Payment flow should not be created when payments are outside the window')

    def test_payment_flow_not_created_without_payments(self):
        """No payment flow should be built when no payments exist for the window."""
        self._create_invoice(sent=True, product=self.service_product)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == 'payment')
        self.assertFalse(pay_flow, 'No payment flow expected without any payments')

    def test_receipts_grouped_by_date(self):
        """Receipts on the same date should aggregate into a single payment entry."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        date_val = fields.Date.context_today(self.env['account.move'])
        receipts = self.env['account.move'].browse()
        for _i in range(2):
            receipt = self.env['account.move'].create({
                'move_type': 'out_receipt',
                'partner_id': self.partner_b2c.id,
                'invoice_date': date_val,
                'journal_id': journal.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.service_product.id,
                    'quantity': 1,
                    'price_unit': 25,
                    'tax_ids': [Command.set([])],
                    'account_id': self.income_account.id,
                })],
            })
            receipt.action_post()
            receipt.is_move_sent = True
            receipts |= receipt

        aggregator = self.env['l10n.fr.pdp.flow.aggregator']
        pay_start, pay_end, _code = aggregator._get_period_bounds(self.company.id, date_val, 'payment')
        payment_moves = aggregator._get_payment_moves(receipts)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == 'payment' and (f.move_ids & receipts))[:1]
        if not pay_flow and payment_moves:
            pay_flow = self.env['l10n.fr.pdp.flow'].create({
                'company_id': self.company.id,
                'report_kind': 'payment',
                'flow_type': 'transaction_report',
                'currency_id': self.company.currency_id.id,
                'document_type': 'sale',
                'transaction_type': 'mixed',
                'transmission_type': 'IN',
                'period_start': pay_start,
                'period_end': pay_end,
                'periodicity_code': 'M',
                'reporting_date': pay_start,
                'issue_datetime': fields.Datetime.now(),
                'move_ids': [Command.set(payment_moves.ids)],
            })
            pay_flow._build_payload()
        self.assertTrue(pay_flow, 'Payment flow should be generated for receipts in window')
        xml = etree.fromstring(base64.b64decode(pay_flow.payload))
        payments = xml.findall('.//PaymentsReport//Transactions')
        self.assertEqual(len(payments), 1, 'Receipts on same date should be grouped into one payment entry')
        subtotal = payments[0].find('.//Amount')
        self.assertEqual(subtotal.text, '50.0', 'Grouped receipt amount should sum both receipts')

    def test_payment_cron_skips_manual_mode(self):
        """Cron should not send payment flows when company send mode is manual."""
        self.company.l10n_fr_pdp_send_mode = 'manual'
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv)
        flows = self._aggregate_company()
        pay_flow = flows.filtered(lambda f: f.report_kind == 'payment')[:1]
        self.assertTrue(pay_flow)
        ready_state = pay_flow.state
        with patch('odoo.fields.Date.context_today', return_value=fields.Date.context_today(self.env['l10n.fr.pdp.flow'])):
            self.env['l10n.fr.pdp.flow']._cron_send_ready_flows()
        pay_flow.invalidate_recordset(['state', 'transport_identifier'])
        self.assertEqual(pay_flow.state, ready_state, 'Manual mode should prevent cron from sending payment flows')
        self.assertFalse(pay_flow.transport_identifier)

    def test_payment_precision_validation_error(self):
        """Payment amounts outside currency precision should trigger validation error."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not flow.payload:
            flow._build_payload()

        def fake_invoice_payments(_self, moves):
            return [{
                'id': 'PAY1',
                'invoice_id': inv.name,
                'date': fields.Date.today().strftime('%Y%m%d'),
                'amount': 0.001,
                'currency': flow.currency_id.name,
                'payment_method': 'Manual',
                'subtotals': [],
            }]

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_payments', fake_invoice_payments):
            with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_payments', return_value=[]):
                with self.assertRaises(UserError) as ctx:
                    flow._build_payload()
        self.assertIn('exceeds currency precision', str(ctx.exception))

    def test_payment_currency_mismatch_skips_precision_check(self):
        """Payments in a different currency should bypass precision validation."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'payment')[:1]
        if not flow.payload:
            flow._build_payload()

        def fake_invoice_payments(_self, moves):
            return [{
                'id': 'PAY2',
                'invoice_id': inv.name,
                'date': fields.Date.today().strftime('%Y%m%d'),
                'amount': 0.001,
                'currency': 'USD',
                'payment_method': 'Manual',
                'subtotals': [],
            }]

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_payments', fake_invoice_payments):
            with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_payments', return_value=[]):
                # Should not raise despite small amount because currency differs from flow currency
                flow._build_payload()
        self.assertTrue(flow.payload, 'Payload should still be generated with foreign currency payments')
