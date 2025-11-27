from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.l10n_fr_pdp_reports.models.pdp_payload import PdpPayloadBuilder

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpFlowsBasic(PdpTestCommon):
    def test_single_invoice_ready_flow(self):
        """IN transaction flow built and ready for a single sent invoice."""
        self._create_invoice(sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')
        self.assertGreaterEqual(len(flow), 1, 'Expected at least one transaction flow')
        flow = flow[:1]
        self.assertEqual(flow.state, 'ready', 'Flow should be ready after payload build')
        self.assertEqual(flow.transmission_type, 'IN', 'First flow must be IN')
        self.assertTrue(flow.payload, 'Payload must be generated')

    def test_invoice_not_sent_flags_error_status(self):
        """Posted invoice not sent -> PDP status error."""
        inv = self._create_invoice(sent=False)
        self._run_aggregation()
        inv.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(inv.l10n_fr_pdp_status, 'error', 'Unsent posted invoice must be in PDP error')

    def test_b2c_daily_summary_multiple_days(self):
        """B2C invoices on different days generate per-day summaries in payload."""
        day1 = fields.Date.from_string('2025-01-05')
        day2 = fields.Date.from_string('2025-01-06')
        self._create_invoice(date_val=day1, sent=True)
        self._create_invoice(date_val=day2, sent=True)
        flows = self._run_aggregation()
        tx_flows = flows.filtered(lambda f: f.report_kind == 'transaction')
        self.assertTrue(tx_flows, 'Transaction flow should exist')
        for flow in tx_flows:
            dates = {m.invoice_date or m.date for m in flow.move_ids}
            builder = PdpPayloadBuilder(flow)
            report_vals = builder._build_transaction_report_vals(flow.move_ids)
            summaries = report_vals.get('transaction_summaries') or []
            self.assertEqual(
                len(summaries), len(dates),
                'Flow %s expected %s summaries for dates %s, got %s' % (
                    flow.id, len(dates), dates, len(summaries)),
            )

    def test_flow_rebuilds_when_entering_grace(self):
        """A pending flow should be rebuilt when moving from open to grace."""
        inv_date = fields.Date.from_string('2025-02-05')
        self._create_invoice(date_val=inv_date, sent=True)

        open_day = fields.Date.from_string('2025-02-07')   # within period 1-10
        grace_day = fields.Date.from_string('2025-02-15')  # after period end, before due date (20th)

        with patch('odoo.fields.Date.context_today', return_value=open_day):
            flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch('odoo.fields.Date.context_today', return_value=open_day):
            flow.invalidate_recordset(['state', 'period_status'])
            self.assertEqual(flow.period_status, 'open')
            self.assertEqual(flow.state, 'pending')

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            self._aggregate_company()
        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            flow.invalidate_recordset(['state', 'period_status'])
            self.assertEqual(flow.period_status, 'grace')
            self.assertEqual(flow.state, 'ready')
