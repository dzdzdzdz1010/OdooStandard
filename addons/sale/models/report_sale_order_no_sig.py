from odoo import models


class ReportSaleOrderNoSig(models.AbstractModel):
    _name = 'report.sale.report_saleorder_no_sig'
    _description = 'Custom Sale Report Parser'

    def _get_report_values(self, docids, data=None):
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name('sale.report_saleorder_no_sig')
        # get the records selected for this rendering of the report
        docs = self.env['sale.order'].browse(docids)
        # return a custom rendering context
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': docs,
            'hide_signature': report.hide_signature if report else False,
        }
