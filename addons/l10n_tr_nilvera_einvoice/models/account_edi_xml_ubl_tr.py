import math
from collections import defaultdict

from lxml import etree
from num2words import num2words

from odoo import _, Command, api, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict, html2plaintext
from odoo.tools.misc import clean_context

from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES
from odoo.addons.base.models.res_partner_bank import sanitize_account_number
from odoo.addons.l10n_tr_nilvera_einvoice.tools.clean_node_dict import clean_node_dict
from odoo.addons.l10n_tr_nilvera_einvoice.tools.ubl_tr_invoice import TrInvoice


class AccountEdiXmlUblTr(models.AbstractModel):
    _name = "account.edi.xml.ubl.tr"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL-TR 1.2"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the TR UBL version, we always want the Shipment with ID empty node, due to it being required.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        shipment_id_elements = xml_root.findall('.//cac:Shipment/cbc:ID', namespaces=xml_root.nsmap)
        for element in shipment_id_elements:
            if element.text == 'NO_ID':
                element.text = ''
        return etree.tostring(xml_root, xml_declaration=True, encoding='UTF-8'), errors

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return '%s_einvoice.xml' % invoice.name.replace("/", "_")

    def _get_tax_category_code(self, customer, supplier, tax):
        # OVERRIDES account.edi.ubl_21
        if tax and tax.amount < 0:  # This is a withholding
            return '9015'
        return '0015'

    def _add_invoice_currency_vals(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_currency_vals(vals)
        vals['currency_dp'] = 2  # Force 2 decimal places everywhere

    # -------------------------------------------------------------------------
    # EXPORT: TEMPLATES
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Check the customer status if it hasn't been done before as it's needed for profile_id
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'not_checked':
            invoice.partner_id._check_nilvera_customer()

        if invoice._l10n_tr_nilvera_einvoice_check_negative_lines():
            raise UserError(self.env._("Nilvera portal cannot process negative quantity nor negative price on invoice lines"))

        # Using _get_sequence_format_param to extract the invoice sequence components for various formats.
        # To send an invoice to Nilvera, the format needs to follow ABC2009123456789.
        _, parts = invoice._get_sequence_format_param(invoice.name)
        prefix, year, number = parts['prefix1'][:3], parts['year'], str(parts['seq']).zfill(9)
        invoice_id = f"{prefix.upper()}{year}{number}"

        document_node.update({
            'cbc:CustomizationID': {'_text': 'TR1.2'},
            'cbc:ProfileID': {'_text': self._get_tr_profile_id(invoice)},
            'cbc:ID': {'_text': invoice_id},
            'cbc:CopyIndicator': {'_text': 'false'},
            'cbc:UUID': {'_text': invoice.l10n_tr_nilvera_uuid},
            'cbc:DueDate': None,
            'cbc:InvoiceTypeCode': {'_text': 'ISTISNA' if invoice.l10n_tr_is_export_invoice else invoice.l10n_tr_gib_invoice_type},
            'cbc:CreditNoteTypeCode': {'_text': 'IADE'} if vals['document_type'] == 'credit_note' else None,
            'cbc:PricingCurrencyCode': {'_text': invoice.currency_id.name.upper()}
                if vals['currency_id'] != vals['company_currency_id'] else None,
            'cbc:LineCountNumeric': {'_text': len(invoice.line_ids)},
            'cbc:BuyerReference': None,  # Nilvera will reject any <BuyerReference> tag, so remove it
            'cbc:Note': {
                '_text': html2plaintext(invoice.narration, include_references=False) if invoice.narration else None,
            },
        })

        document_node['cac:OrderReference']['cbc:IssueDate'] = {'_text': invoice.invoice_date}

        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'earchive':
            document_node['cac:AdditionalDocumentReference'] = {
                'cbc:ID': {'_text': 'ELEKTRONIK'},
                'cbc:IssueDate': {'_text': invoice.invoice_date},
                'cbc:DocumentTypeCode': {'_text': 'SEND_TYPE'},
            }
        document_node['cbc:Note'] = [
            document_node['cbc:Note'],
            {'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual_signed, self.env.ref('base.TRY')), 'note_attrs': {}}
        ]
        if vals['invoice'].currency_id.name != 'TRY':
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual, vals['invoice'].currency_id), 'note_attrs': {}})
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_invoice_currency_exchange_rate(invoice)})

    @api.model
    def _l10n_tr_get_amount_integer_partn_text_note(self, amount, currency):
        sign = math.copysign(1.0, amount)
        amount_integer_part, amount_decimal_part = divmod(abs(amount), 1)
        amount_decimal_part = int(amount_decimal_part * 100)

        text_i = num2words(amount_integer_part * sign, lang="tr") or 'Sifir'
        text_d = num2words(amount_decimal_part * sign, lang="tr") or 'Sifir'
        return f'YALNIZ : {text_i} {currency.name} {text_d} {currency.currency_subunit_label}'.upper()

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        """Extend invoice accounting customer party nodes for TR E-Invoicing.

        For export invoice, the AccountingCustomerParty is set to the static
        Turkish Ministry of Customs and Trade node.

        :param document_node: dict representing the invoice XML structure to modify.
        :param vals: dict containing invoice-related values, including 'invoice'.
        """
        super()._add_invoice_accounting_customer_party_nodes(document_node, vals)
        if vals['invoice'].l10n_tr_is_export_invoice:
            document_node['cac:AccountingCustomerParty'] = {'cac:Party': self._get_ministry_party_node()}

    @api.model
    def _add_invoice_buyer_customer_party_nodes(self, document_node, vals):
        """Adds BuyerCustomerParty node for TR E-Invoicing.

        For export invoices, a buyer party node is created based on the customer,
        and the PartyIdentification values are updated to indicate an export customer.

        :param document_node: dict representing the invoice XML structure to modify.
        :param vals: dict containing invoice-related values, including 'invoice'.
        """
        if vals['invoice'].l10n_tr_is_export_invoice:
            buyer_party_node = self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'buyer'})
            buyer_party_node['cac:PartyIdentification'] = [{'cbc:ID': {
                '_text': 'EXPORT',
                'schemeID': 'PARTYTYPE',
                },
            }]
            document_node['cac:BuyerCustomerParty'] = {'cac:Party': buyer_party_node}

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']
        if 'picking_ids' in invoice._fields and invoice.picking_ids:
            document_node['cac:Delivery']['cbc:ID'] = {'_text': invoice.picking_ids[0].name}
            document_node['cac:Delivery']['cbc:ActualDeliveryDate'] = {'_text': invoice.delivery_date}
        else:
            document_node['cac:Delivery'] = None

    def _l10n_tr_get_invoice_currency_exchange_rate(self, invoice):
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            from_currency=invoice.currency_id,
            to_currency=invoice.company_currency_id,
            company=invoice.company_id,
            date=invoice.invoice_date,
        )
        # Nilvera Portal accepts the exchange rate for 6 decimals places only.
        return f'KUR : {conversion_rate:.6f} TL'

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        payment_means_node['cbc:InstructionID'] = None
        payment_means_node['cbc:PaymentID'] = None

    def _add_invoice_exchange_rate_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if vals['currency_id'] != vals['company_currency_id']:
            document_node['cac:PricingExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': vals['currency_name']},
                'cbc:TargetCurrencyCode': {'_text': vals['company_currency_id'].name},
                'cbc:CalculationRate': {'_text': round(invoice.currency_id._get_conversion_rate(invoice.currency_id, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date), 6)},
                'cbc:Date': {'_text': invoice.invoice_date},
            }

    def _l10n_tr_get_total_invoice_discount_amount(self, vals):
        invoice = vals['invoice']
        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in {'line_note', 'line_section'})
        return sum(
            line.currency_id.round(line.price_unit * line.quantity * (line.discount / 100))
            for line in invoice_lines
        )

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        super()._add_document_allowance_charge_nodes(document_node, vals)
        for node in document_node['cac:AllowanceCharge']:
            node['cbc:AllowanceChargeReasonCode'] = None

        total_discount_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        if total_discount_amount:
            document_node['cac:AllowanceCharge'].append({
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReason': {'_text': "Discount"},
                'cbc:Amount': {
                    '_text': self.format_float(total_discount_amount, vals['currency_dp']),
                    'currencyID': vals['currency_name'],
                },
            })

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        """Adds tax total nodes to a document line.

        For Turkish withholding invoices TEVKIFAT, this method
        delegates to add_withholding_document_line_tax_total_nodes.
        Otherwise, it falls back to the default behavior.

        :param line_node: XML node representing the invoice line.
        :param vals: Dictionary containing the invoice data.
        :return: Updated XML line node with tax total information.
        """
        if vals['invoice'].l10n_tr_gib_invoice_type == 'TEVKIFAT':
            return self._add_withholding_document_line_tax_total_nodes(line_node, vals)
        return super()._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_line_delivery_nodes(self, line_node, vals):
        """Add delivery information to an invoice line node for export invoices.

        For export invoice, it builds the cac:Delivery section of the
        UBL TR XML for invoice lines. The delivery node includes
        address, incoterms, shipment, and customs-related details.

        :param line_node: dict representing the invoice line XML structure to update.
        :param vals: dict containing invoice line data.
        """
        move_line = vals['base_line']['record']
        if move_line.move_id.l10n_tr_is_export_invoice:
            line_node['cac:Delivery'] = {
                'cac:DeliveryAddress': {
                    'cbc:StreetName': {'_text': move_line.move_id.partner_id.street},
                    'cbc:CitySubdivisionName': {'_text': move_line.move_id.partner_id.city},
                    'cbc:CityName': {'_text': move_line.move_id.partner_id.state_id.with_context(lang='tr_TR').name},
                    'cbc:PostalZone': {'_text': move_line.move_id.partner_id.zip},
                    'cac:Country': {'cbc:Name': {'_text': move_line.move_id.partner_id.country_id.with_context(lang='tr_TR').name}},
                },
                'cac:DeliveryTerms': {
                    'cbc:ID': {'_text': move_line.move_id.invoice_incoterm_id.code, 'schemeID': 'INCOTERMS'},
                },
                'cac:Shipment': {
                    'cbc:ID': {'_text': 'NO_ID'},
                    'cac:GoodsItem': {'cbc:RequiredCustomsID': {'_text': move_line.l10n_tr_ctsp_number or move_line.product_id.l10n_tr_ctsp_number}},
                    'cac:ShipmentStage': {'cbc:TransportModeCode': {'_text': move_line.move_id.l10n_tr_shipping_type}},
                },
            }

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        """Adds tax total nodes to the invoice document.

        For Turkish withholding invoices ('TEVKIFAT'), this method
        delegates to `_add_withholding_document_tax_total_nodes`.
        Otherwise, it uses the default tax total behavior.

        :param document_node: XML node representing the full invoice document.
        :param vals: Dictionary containing the invoice data.
        :return: lxml.etree.Element or similar XML node representing the updated invoice document.

        """
        if vals['invoice'].l10n_tr_gib_invoice_type == 'TEVKIFAT':
            return self._add_withholding_document_tax_total_nodes(document_node, vals)
        return super()._add_document_tax_total_nodes(document_node, vals)

    def _add_withholding_document_tax_total_nodes(self, line_node, vals):
        """Extends the aggregation of tax details to include Turkish (TR) withholding-specific amounts
        for an invoice line.

        This method performs the following:
            - Aggregates tax details across all base lines.
            - Adds two fields per grouping key:
                - tr_total_taxed_amount: Total tax amount used in the withholding tax line.
                - tr_total_taxed_residual_amount: Total tax amount after withholding, shown in the tax line.
            - Splits aggregated tax details into normal taxes and withholding taxes.
            - Updates `line_node` with:
                - 'cac:TaxTotal' for normal taxes
                - 'cac:WithholdingTaxTotal' for withholding taxes (if the document is an invoice)

        If there is a 20% tax and 18% is withheld on ₺10:
            - tr_total_taxed_amount = ₺2
            - tr_total_taxed_residual_amount = ₺0.2

        :param line_node: XML node representing the invoice line to be updated.
        :param vals: Dictionary containing invoice data and base lines.
        """
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], self.tax_grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)

        for base_line, aggregated_values in base_lines_aggregated_tax_details:
            for grouping_key in aggregated_values:
                taxes_data = base_line.get('tax_details', {}).get('taxes_data', [])
                rounding = base_line.get('record').currency_id.rounding

                # Sum of positive tax amounts (with rounding check)
                total_taxed_amount = sum(
                    tax_line['tax_amount']
                    for tax_line in taxes_data
                    if float_compare(tax_line['tax_amount'], 0, precision_rounding=rounding) > 0
                )

                # Sum of all tax amounts
                total_residual_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data)

                # Update values_per_grouping_key
                group_vals = aggregated_tax_details[grouping_key]
                group_vals['tr_total_taxed_amount'] = group_vals.get('tr_total_taxed_amount', 0.0) + total_taxed_amount
                group_vals['tr_total_taxed_residual_amount'] = group_vals.get('tr_total_taxed_residual_amount', 0.0) + total_residual_amount

        aggregated_tax_details_by_l10n_tr_tax_withholding_code_id = {'tax': defaultdict(dict), 'withholding_tax': defaultdict(dict)}

        for grouping_key, values in aggregated_tax_details.items():
            if grouping_key:
                key = 'withholding_tax' if (l10n_tr_tax_withheld := grouping_key['l10n_tr_tax_withheld']) else 'tax'
                aggregated_tax_details_by_l10n_tr_tax_withholding_code_id[key][l10n_tr_tax_withheld][grouping_key] = values

        line_node['cac:TaxTotal'] = [
            self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line'})
            for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['tax'].values()
        ]
        if vals['document_type'] == 'invoice':
            line_node['cac:WithholdingTaxTotal'] = [
                self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line', 'withholding': True, 'sign': -1})
                for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['withholding_tax'].values()
            ]

    def _add_withholding_document_line_tax_total_nodes(self, line_node, vals):
        """Extend aggregation of line tax details to include Turkish (TR) withholding-specific amounts.

        For each tax grouping key, this method adds two fields:
            - tr_total_taxed_amount: The total tax amount applied to the line before withholding.
            - tr_total_taxed_residual_amount: The remaining tax amount after withholding.

        If there is a 20% tax and 18% is withheld on ₺10:
            - tr_total_taxed_amount = ₺2
            - tr_total_taxed_residual_amount = ₺0.2

        :param line_node: The invoice line node containing tax details.
        :param vals: Tax values used to compute withholding amounts.
        """
        encountered_groups = set()
        base_line = vals['base_line']
        tax_details = base_line['tax_details']
        taxes_data = tax_details['taxes_data']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, self.tax_grouping_function)

        for tax_data in taxes_data:
            grouping_key = self.tax_grouping_function(base_line, tax_data)
            if isinstance(grouping_key, dict):
                grouping_key = frozendict(grouping_key)
            already_accounted = grouping_key in encountered_groups
            encountered_groups.add(grouping_key)
            if not already_accounted:
                taxes_data = base_line.get('tax_details', {}).get('taxes_data', [])
                rounding = base_line.get('record').currency_id.rounding

                total_taxed_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data if float_compare(tax_line['tax_amount'], 0, precision_rounding=rounding) > 0)
                total_residual_amount = sum(tax_line['tax_amount'] for tax_line in taxes_data)

                group_vals = aggregated_tax_details[grouping_key]
                group_vals['tr_total_taxed_amount'] = group_vals.get('tr_total_taxed_amount', 0.0) + total_taxed_amount
                group_vals['tr_total_taxed_residual_amount'] = group_vals.get('tr_total_taxed_residual_amount', 0.0) + total_residual_amount

        aggregated_tax_details_by_l10n_tr_tax_withholding_code_id = {'tax': defaultdict(dict), 'withholding_tax': defaultdict(dict)}

        for grouping_key, values in aggregated_tax_details.items():
            if grouping_key:
                key = 'withholding_tax' if (l10n_tr_tax_withheld := grouping_key['l10n_tr_tax_withheld']) else 'tax'
                aggregated_tax_details_by_l10n_tr_tax_withholding_code_id[key][l10n_tr_tax_withheld][grouping_key] = values

        line_node['cac:TaxTotal'] = [
            self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line'})
            for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['tax'].values()
        ]
        if vals['document_type'] == 'invoice':
            line_node['cac:WithholdingTaxTotal'] = [
                self._get_withholding_tax_total_node({**vals, 'aggregated_tax_details': tax_details, 'role': 'line', 'withholding': True, 'sign': -1})
                for tax_details in aggregated_tax_details_by_l10n_tr_tax_withholding_code_id['withholding_tax'].values()
            ]

    def _get_address_node(self, vals):
        partner = vals['partner']

        return {
            'cbc:StreetName': {'_text': ' '.join(s for s in [partner.street, partner.street2] if s)},
            'cbc:CitySubdivisionName': {'_text': partner.city},
            'cbc:CityName': {'_text': partner.state_id.name},
            'cbc:PostalZone': {'_text': partner.zip},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': partner.country_id.code},
                'cbc:Name': {'_text': partner.country_id.with_context(lang='tr_TR').name},
            }
        }

    def _get_invoice_line_node(self, vals):
        """Generate the invoice line XML node dictionary.

        Extends the base line node by adding delivery-specific nodes.
        Uses context to skip TR reason code processing.

        :param vals: dict with invoice line data.
        :return: invoice line node dict ready for XML rendering.
        """
        line_node = super(AccountEdiXmlUblTr, self.with_context(skip_tr_reason_code=True))._get_invoice_line_node(vals)
        self._add_invoice_line_delivery_nodes(line_node, vals)
        return line_node

    def _get_invoice_node(self, vals):
        """Generate and clean the invoice XML node dictionary.

        Extends the base invoice node by adding buyer/customer party nodes
        and removing child nodes not defined in the template while keeping UBL attributes.

        :param vals: dict with invoice data.
        :return: cleaned invoice node dict for XML rendering.
        """
        document_node = super()._get_invoice_node(vals)
        self._add_invoice_buyer_customer_party_nodes(document_node, vals)
        return clean_node_dict(document_node, self._get_document_template({'document_node': document_node, 'document_type': 'invoice'}))

    def _get_document_template(self, vals):
        """Determines the document template to use based on the provided values.

        If the document is a Turkish invoice (CustomizationID 'TR1.2' and document_type 'invoice'),
        it returns the `TrInvoice` template. Otherwise, it falls back to the default implementation.

        :param vals: Dictionary containing document data, including 'document_node' and 'document_type'.
        :return: Document template class to be used for generating the document.
        """
        if vals['document_node']['cbc:CustomizationID']['_text'] == 'TR1.2' and vals['document_type'] == 'invoice':
            return TrInvoice
        return super()._get_document_template(vals)

    @api.model
    def _get_ministry_party_node(self):
        """Return the fixed ministry (party) information required for TR E-invoicing.

        This method provides identification, address, tax, and naming
        details of the Turkish Ministry of Customs and Trade.

        :return: dict containing ministry party node.
        """
        return {
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': '1460415308',
                    'schemeID': 'VKN',
                },
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': 'Gümrük ve Ticaret Bakanlığı Gümrükler Genel Müdürlüğü- Bilgi İşlem Dairesi Başkanlığı'},
            },
            'cac:PostalAddress': {
                'cbc:CitySubdivisionName': {'_text': 'Ulus'},
                'cbc:CityName': {'_text': 'Ankara'},
                'cac:Country': {'cbc:Name': {'_text': 'Türkiye'}},
            },
            'cac:PartyTaxScheme': {
                'cac:TaxScheme': {'cbc:Name': {'_text': 'Ulus'}},
            },
        }

    def _get_party_node(self, vals):
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        party_node = {
            'cac:PartyIdentification': self._get_party_identification_node_list(partner),
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cac:TaxScheme': {
                    'cbc:Name': {
                        '_text': partner.l10n_tr_tax_office_id.name,
                    }
                }
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            }
        }
        if not partner.is_company:
            name_parts = partner.name.split(' ', 1)
            party_node['cac:Person'] = {
                'cbc:FirstName': {'_text': name_parts[0]},
                # If no family name is present, use a zero-width space (U+200B) to ensure the XML tag is rendered. This is required by Nilvera.
                'cbc:FamilyName': {'_text': name_parts[1] if len(name_parts) > 1 else '\u200B'},
            }
        return party_node

    def _get_party_identification_node_list(self, partner):
        official_categories = partner.category_id._get_l10n_tr_official_categories()
        return [
            {
                'cbc:ID': {
                    '_text': partner.vat,
                    'schemeID': 'VKN' if partner.is_company else 'TCKN',
                },
            },
            *(
                {
                    'cbc:ID': {
                        '_text': category.name,
                        'schemeID': category.parent_id.name,
                    },
                }
                for category in partner.category_id
                if category.parent_id in official_categories
            ),
        ]

    def _get_tax_category_node(self, vals):
        """Overrides UBL 21 to returns the tax category node for a line or invoice, including TR-specific fields.

        - For lines with Turkish withholding (`l10n_tr_tax_withheld`), returns a minimal
        TaxScheme node with the tax name and type code.
        - For other lines, it extends the default tax category node to include:
            - `cbc:TaxExemptionReasonCode`: The TR tax exemption code.
            - `cbc:TaxExemptionReason`: The localized TR tax exemption name.
        These fields are only added if a TR exemption is set and the context does not skip it.

        :param vals: Dictionary containing: grouping_key & invoice record.
        :return: dict representing the XML structure of the tax category node.
        """
        grouping_key = vals['grouping_key']
        if grouping_key.get('l10n_tr_tax_withheld'):
            return {
                'cac:TaxScheme': {
                    'cbc:Name': {'_text': grouping_key['name']},
                    'cbc:TaxTypeCode': {'_text': grouping_key['tax_type_code']},
                },
            }
        is_withholding = grouping_key['tax_category_code'] == '9015'
        tax_category_node = {
            'cac:TaxScheme': {
                'cbc:Name': {'_text': 'KDV Tevkifatı' if is_withholding else 'Gerçek Usulde KDV'},
                'cbc:TaxTypeCode': {'_text': grouping_key['tax_category_code']}
            }
        }
        tax_invoice_exemption = vals['invoice'].l10n_tr_exemption_code_id
        if self.env.context.get('skip_tr_reason_code') or not tax_invoice_exemption:
            return tax_category_node
        tax_category_node.update({
            'cbc:TaxExemptionReasonCode': {'_text': tax_invoice_exemption.code},
            'cbc:TaxExemptionReason': {'_text': tax_invoice_exemption.with_context(lang='tr_TR').name},
        })
        return tax_category_node

    def _get_tax_subtotal_node(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cac:TaxCategory']['cbc:Percent'] = None
        return tax_subtotal_node

    @api.model
    def _get_tr_profile_id(self, invoice):
        """Determine the TR profile ID for the given invoice.

        - If the customer is an e-invoice user and the invoice has a
          l10n_tr_gib_invoice_scenario, return that scenario.
        - If the invoice is marked as an export invoice, return "IHRACAT".
        - Otherwise:
            • Return "TEMELFATURA" if the customer is an e-invoice user.
            • Return "EARSIVFATURA" for e-archive invoices.

        :param invoice: account.move record (the invoice).
        :return: str, TR profile ID to be used in E-invoicing.
        """
        if (is_einvoice := invoice.l10n_tr_nilvera_customer_status == 'einvoice') and invoice.l10n_tr_gib_invoice_scenario:
            return invoice.l10n_tr_gib_invoice_scenario
        if invoice.l10n_tr_is_export_invoice:
            return 'IHRACAT'
        return 'TEMELFATURA' if is_einvoice else 'EARSIVFATURA'

    @api.model
    def _get_withholding_tax_total_node(self, vals):
        """Build the TaxTotal node for withholding taxes in TR E-Invoicing.

        This method calculates total and subtotal withholding tax amounts.

        :param vals: dict containing tax details, currency info, and related data.
        :return: dict representing the withholding tax total node.
        """
        aggregated_tax_details = vals['aggregated_tax_details']
        currency_suffix = vals['currency_suffix']
        currency_name = vals['currency_name']
        precision = vals['currency_dp']
        sign = vals.get('sign', 1)
        is_withholding = vals.get('withholding')

        def get_tax_amount_total():
            """Compute total tax amount depending on whether it is withholding."""
            if is_withholding:
                return sum(
                    details[f'tax_amount{currency_suffix}']
                    for grouping_key, details in aggregated_tax_details.items()
                    if grouping_key
                )
            return sum(
                values['tr_total_taxed_residual_amount']
                for grouping_key, values in aggregated_tax_details.items()
                if grouping_key
            )

        def get_total_tax_subtotal_amount(details):
            """Compute the total taxable amount depending on whether it is withholding."""
            return details['tr_total_taxed_amount'] if is_withholding else details.get(f'base_amount{currency_suffix}', 0)

        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * get_tax_amount_total(), precision),
                'currencyID': currency_name,
            },
            'cac:TaxSubtotal': [
                {
                    'cbc:TaxableAmount': {
                        '_text': self.format_float(get_total_tax_subtotal_amount(details), precision),
                        'currencyID': currency_name,
                    },
                    'cbc:TaxAmount': {
                        '_text': self.format_float(sign * details[f'tax_amount{currency_suffix}'], precision),
                        'currencyID': currency_name,
                    },
                    'cbc:Percent': {
                        # The percentatge can't be a float as it is expected to return as an integer
                        '_text': grouping_key['percent_withheld'] if is_withholding else grouping_key['amount'],
                    },
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key}),
                }
                for grouping_key, details in aggregated_tax_details.items()
                if grouping_key
            ],
        }

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        invoice = vals['invoice']

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]

        # allowance_total_amount needs to have a value even if 0.0 otherwise it's blank in the Nilvera PDF.
        total_allowance_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        monetary_total_node['cbc:AllowanceTotalAmount'] = {
            '_text': self.format_float(total_allowance_amount, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }

        # <cbc:PrepaidAmount> tag is not supported by Nilvera. so it is removed and <cbc:PayableAmount> holds the
        # amount_total so that the total invoice amount (in invoice currency) is preserved.
        monetary_total_node['cbc:PrepaidAmount'] = None
        monetary_total_node['cbc:PayableAmount'] = {
            '_text': self.format_float(invoice.amount_total, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }
        # For invoices registered as Export, the payable amount is set to the total amount
        # without tax, as required by Turkish e-invoicing regulations.
        if invoice.l10n_tr_gib_invoice_type == "IHRACKAYITLI":
            document_node["cac:LegalMonetaryTotal"]["cbc:PayableAmount"]["_text"] = document_node["cac:LegalMonetaryTotal"]["cbc:TaxExclusiveAmount"]["_text"]

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_document_line_allowance_charge_nodes(line_node, vals)
        for allowance_charge_node in line_node['cac:AllowanceCharge']:
            allowance_charge_node['cbc:AllowanceChargeReasonCode'] = None
            discount_percentage = vals.get('discount_amount') / vals.get('gross_subtotal') if vals.get('gross_subtotal') else 0
            allowance_charge_node['cbc:MultiplierFactorNumeric'] = {
            '_text': self.format_float(discount_percentage, vals['currency_dp']),
            }

    def _add_document_line_item_nodes(self, line_node, vals):
        super()._add_document_line_item_nodes(line_node, vals)
        if line_node.get('cac:Item', {}).get('cac:StandardItemIdentification'):
            line_node['cac:Item']['cac:StandardItemIdentification'] = None

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        # No InvoiceLine/Item/ClassifiedTaxCategory in Turkey
        pass

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # Start and End Dates on Invoice Lines is not allowed in Turkey
        pass

    @api.model
    def tax_grouping_function(self, base_line, tax_data):
        """Build a grouping key for tax aggregation, extended for Turkish (TR) withholding taxes.

        This method extends the default tax grouping logic to include TR-specific
        withholding details. It constructs a grouping key for each tax line and
        appends withholding-related fields when applicable.

        Specifically, for invoices of type TEVKIFAT with a withholding tax code,
        the following fields are added to the grouping key:
            - l10n_tr_tax_withheld: The ID of the withholding tax code.
            - percent_withheld: The percentage of tax to be withheld (as an integer).
            - name: The localized name of the withholding tax (in Turkish).
            - tax_type_code: The code of the withholding tax.

        :param dict base_line: The base invoice line containing the record and tax details.
        :param dict tax_data: The dictionary containing the tax and its computed values.
        :return: The grouping key dictionary for this tax line, including TR withholding details if applicable.
        """
        invoice = base_line["record"].move_id
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id
        tax = tax_data["tax"]

        grouping_key = {
            "tax_category_code": self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
            **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
            "amount": tax.amount if tax else 0.0,
            "amount_type": tax.amount_type if tax else "percent",
            "l10n_tr_tax_withheld": tax.l10n_tr_tax_withholding_code_id.id,
        }

        if invoice.l10n_tr_gib_invoice_type == "TEVKIFAT" and tax.l10n_tr_tax_withholding_code_id:
            withholding_code = tax.l10n_tr_tax_withholding_code_id
            grouping_key.update(
                {
                    "percent_withheld": int(withholding_code.percentage * 100),
                    "name": withholding_code.with_context(lang="tr_TR").name,
                    "tax_type_code": withholding_code.code,
                },
            )

        return grouping_key

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------
    @api.model
    def _l10n_tr_import_profile_id(self, tree):
        return self._find_value(".//cbc:ProfileID", tree)

    @api.model
    def _l10n_tr_import_partner_node_name(self, tree):
        profile_id = self._l10n_tr_import_profile_id(tree)
        if profile_id == "IHRACAT":
            return "BuyerCustomer"
        return "AccountingCustomer"

    @api.model
    def _l10n_tr_import_invoice_type_code(self, tree):
        return self._find_value(".//cbc:InvoiceTypeCode", tree)

    @api.model
    def _l10n_tr_import_postal_address_from_xml(self, tree, node_name):
        postal_address_cac = f".//cac:{node_name}Party//cac:PostalAddress"

        return {
            "country_code": self._find_value(f"{postal_address_cac}/cac:Country/cbc:IdentificationCode", tree),
            "country_name": self._find_value(f"{postal_address_cac}/cac:Country/cbc:Name", tree),
            "street": self._find_value(f"{postal_address_cac}/cbc:StreetName", tree),
            "city": self._find_value(f"{postal_address_cac}/cbc:CitySubdivisionName", tree),
            "zip": self._find_value(f"{postal_address_cac}/cbc:PostalZone", tree),
            "state_name": self._find_value(f"{postal_address_cac}/cbc:CityName", tree),
        }

    @api.model
    def _l10n_tr_import_partner_vals_from_xml(self, tree, node_name):
        return {
            "vat": (
                self._find_value(
                    f".//cac:{node_name}Party//cac:PartyLegalEntity//cbc:CompanyID[string-length(text()) > 5]",
                    tree,
                )
                or self._find_value(
                    f'.//cac:{node_name}Party//cac:PartyIdentification//cbc:ID[@schemeID="VKN"][string-length(text()) > 5]',
                    tree,
                )
            ),
            "phone": self._find_value(f".//cac:{node_name}Party//cac:Contact//cbc:Telephone", tree),
            "email": self._find_value(f".//cac:{node_name}Party//cac:Contact//cbc:ElectronicMail", tree),
            "name": (
                self._find_value(f".//cac:{node_name}Party//cac:PartyName//cbc:Name", tree)
                or self._find_value(f".//cac:{node_name}Party//cbc:RegistrationName", tree)
            ),
            "postal_address": self._l10n_tr_import_postal_address_from_xml(tree, node_name),
        }

    @api.model
    def _ensure_partner_address(self, partner, postal_address):
        if not partner or any([
            partner.country_id, partner.street, partner.city,
            partner.zip, partner.state_id,
        ]):
            return

        country = self.env["res.country"]
        if country_code := postal_address.get("country_code"):
            country = country.search([("code", "=", country_code)], limit=1)
        elif country_name := postal_address.get("country_name"):
            country = country.search([("name", "=", country_name)], limit=1)

        state = self.env["res.country.state"]
        if country and (state_name := postal_address.get("state_name")):
            state = state.search([("country_id", "=", country.id), ("name", "=", state_name)], limit=1)

        partner.write(
            {
                "country_id": country.id,
                "street": postal_address.get("street"),
                "city": postal_address.get("city"),
                "zip": postal_address.get("zip"),
                "state_id": state.id,
            },
        )

    @api.model
    def _l10n_tr_resolve_invoice_partner(self, tree, company_id, invoice_values, logs):
        partner_node_name = self._l10n_tr_import_partner_node_name(tree)
        partner_vals = self._l10n_tr_import_partner_vals_from_xml(tree, partner_node_name)

        vat = partner_vals.get("vat")
        if not vat:
            logs.append(_("The partner VAT is missing; cannot retrieve or create the partner."))
            return self.env["res.partner"]

        # Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name)
        partner = self.env["res.partner"]._retrieve_partner(vat=vat, company=company_id)
        is_new_partner = not bool(partner)

        if is_new_partner:
            logs.append(_("No partner found with VAT %s. A new partner is created.", vat))
            # Create and verify partner
            if not partner_vals.get("name") or not partner_vals.get("vat"):
                logs.append(_("Could not create a partner due to name or vat missing"))
                return self.env["res.partner"]

            partner = self.env["res.partner"].create({
                "name": partner_vals.get("name"),
                "phone": partner_vals.get("phone"),
                "email": partner_vals.get("email"),
                "vat": vat,
            })
            logs.append(_("A new partner '%s' has been created.", partner.name))

        self._ensure_partner_address(partner, partner_vals.get("postal_address", {}))

        if is_new_partner:
            partner.l10n_tr_check_nilvera_customer()

        invoice_values["partner_id"] = partner.id
        return partner

    @api.model
    def _l10n_tr_resolve_bank_account(self, tree, partner, invoice_values, logs):
        payment_means = tree.find(".//cac:PaymentMeans", UBL_NAMESPACES)
        if payment_means is None:
            logs.append(_("No bank details were found in the document."))
            return

        bank_account_vals = []
        for acc in payment_means.findall(".//cac:PayeeFinancialAccount", UBL_NAMESPACES):
            bank_account_vals.append({"account_id": sanitize_account_number(self._find_value("./cbc:ID", acc))})

        if not bank_account_vals:
            logs.append(_("No bank details were found in the document."))
            return

        account_numbers = [val["account_id"] for val in bank_account_vals if val["account_id"]]
        existing_accounts = (
            self.env["res.partner.bank"]
            .with_context(active_test=False)
            .search([("account_number", "in", account_numbers), ("partner_id", "=", partner.id)])
        )

        if existing_accounts:
            invoice_values["partner_bank_id"] = existing_accounts[0].id

            if not existing_accounts[0].active:
                existing_accounts[0].active = True
                logs.append(_("An existing bank account %s has been reactivated", existing_accounts[0].account_number))
            return

        ResPartnerBank = self.env["res.partner.bank"].with_env(self.env(context=clean_context(self.env.context)))
        bank_account = ResPartnerBank.create(
            {
                "partner_id": partner.id,
                "account_number": bank_account_vals[0]["account_id"],
            },
        )
        logs.append(_("A new bank account %s has been created.", bank_account.account_number))
        invoice_values["partner_bank_id"] = bank_account.id

    @api.model
    def _l10n_tr_resolve_delivery_details(self, tree, invoice_values):
        delivery_tree = tree.find(".//cac:InvoiceLine/cac:Delivery", UBL_NAMESPACES)
        if delivery_tree is None:
            return

        delivery_terms_id = self._find_value("cac:DeliveryTerms/cbc:ID", delivery_tree)
        transport_mode_code = self._find_value("cac:Shipment/cac:ShipmentStage/cbc:TransportModeCode", delivery_tree)

        invoice_values["l10n_tr_shipping_type"] = transport_mode_code
        invoice_values["invoice_incoterm_id"] = (
            self.env["account.incoterms"].search([("code", "=", delivery_terms_id)], limit=1).id
        )

    @api.model
    def _l10n_tr_resolve_export_exemption(self, tree, invoice_values, logs):
        invoice_type_code = self._l10n_tr_import_invoice_type_code(tree)
        if invoice_type_code not in ["ISTISNA", "IHRACKAYITLI"]:
            return
        tax_category_node = tree.find("./cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory", UBL_NAMESPACES)
        if tax_category_node is not None:
            tax_exemption_reason_code = self._find_value("cbc:TaxExemptionReasonCode", tax_category_node)
            tax_exemption_id = self.env["l10n_tr_nilvera_einvoice.account.tax.code"].search(
                [("code", "=", tax_exemption_reason_code)],
                limit=1,
            )

            if tax_exemption_id:
                invoice_values["l10n_tr_exemption_code_id"] = tax_exemption_id.id
            else:
                logs.append(_("Could not find exemption code with reason '%s'", tax_exemption_reason_code))

    @api.model
    def _l10n_tr_resolve_basic_fields(self, tree, invoice_values, logs):
        profile_id = self._l10n_tr_import_profile_id(tree)
        # under profile_id on xml there is a ID, we will map it to bill reference/reference for bill and invoice
        if profile_id == "IHRACAT":
            invoice_values["l10n_tr_is_export_invoice"] = True
        elif profile_id in ["TEMELFATURA", "KAMU"]:
            # EARSIVFATURA is ignored as it's not in the l10n_tr_gib_invoice_scenario field
            invoice_values["l10n_tr_gib_invoice_scenario"] = profile_id

        invoice_values["l10n_tr_gib_invoice_type"] = self._find_value(".//cbc:InvoiceTypeCode", tree)
        invoice_values["currency_id"], currency_logs = self._import_currency(tree, ".//{*}DocumentCurrencyCode")
        logs.extend(currency_logs)

        invoice_values["invoice_date"] = self._find_value(".//cbc:IssueDate", tree)
        invoice_values["invoice_date_due"] = self._find_value(".//cac:PaymentMeans/cbc:PaymentDueDate", tree)
        invoice_values["ref"] = (
            self._find_value("./cac:OrderReference/cbc:ID", tree)
            or self._find_value("./cbc:ID", tree)
        )
        invoice_values["narration"] = self._import_description(tree, xpaths=["./{*}Note", "./{*}PaymentTerms/{*}Note"])

    @api.model
    def _l10n_tr_find_product_id_by_default_code_or_ctsp(self, vals):
        default_codes = [val[0] for val in vals if val[0]]
        ctsp_numbers = [val[1] for val in vals if val[1]]
        data_list = self.env["product.product"]._read_group(
            domain=[
                "|",
                ("default_code", "in", default_codes),
                ("l10n_tr_ctsp_number", "in", ctsp_numbers),
            ],
            aggregates=["id:recordset"],
            groupby=["default_code", "l10n_tr_ctsp_number"],
        )
        result = {
            "default_codes": {},
            "ctsp_numbers": {},
        }
        for default_code, ctsp_number, records in data_list:
            if default_code and default_code not in result["default_codes"]:
                result["default_codes"][default_code] = records
            if ctsp_number and ctsp_number not in result["ctsp_numbers"]:
                result["ctsp_numbers"][ctsp_number] = records
        return result

    @api.model
    def _l10n_tr_find_tax_id_by_percentage(self, amount, move_type):
        return (
            self.env["account.tax"]
            .search(
                [
                    ("country_id.code", "=", "TR"),
                    ("amount", "=", amount),
                    ("amount_type", "=", "percent"),
                    ("type_tax_use", "=", move_type),
                ],
                limit=1,
                order="sequence",
            )
            .id
        )

    @api.model
    def _l10n_tr_find_tax_id_by_reason_code(self, withholding_code, move_type):
        # There must be only one tax for each withholding code in Nilvera
        # But based on model structure there can be multiple parent tax for each withholding code
        return (
            self.env["account.tax"]
            .search(
                [
                    ("children_tax_ids.l10n_tr_tax_withholding_code_id.code", "=", withholding_code),
                    ("country_id.code", "=", "TR"),
                    ("type_tax_use", "=", move_type),
                ],
                order="sequence",
                limit=1,
            ).id
        )

    @api.model
    def _l10n_tr_find_tax_id_by_tax_details(
        self,
        tax_details_list,
        profile_id,
        invoice_type,
        move_type,
    ):
        """
        Retrieve tax IDs for a list of tax details based on profile ID, invoice type, and account move type.

        :param list[dict] tax_details_list: List of tax detail dictionaries.
        :param str profile_id: ``ProfileID`` value from the XML.
        :param str invoice_type: ``InvoiceTypeCode`` value from the XML.
        :param str move_type: Account move type (``sale`` or ``purchase``).
        :return list[list[int]]: Tax IDs grouped per tax detail entry.
        """

        result = []
        for tax_details in tax_details_list:
            if profile_id == "IHRACAT":
                # this is a tax-exempt export
                tax_id = self._l10n_tr_find_tax_id_by_percentage(0, move_type=move_type)
            elif invoice_type == "TEVKIFAT":
                tax_id = self._l10n_tr_find_tax_id_by_reason_code(
                    tax_details["withholding_reason_code"],
                    move_type=move_type,
                )
            else:
                tax_id = self._l10n_tr_find_tax_id_by_percentage(
                    tax_details["tax_percentage"],
                    move_type=move_type,
                )
            result.append([tax_id] if tax_id else [])
        return result

    @api.model
    def _l10n_tr_import_tax_details(self, line_tree):
        tax_percentage = self._find_value(".//cac:TaxTotal//cac:TaxSubtotal//cbc:Percent", line_tree)
        return {
            "withholding_reason_code": self._find_value(
                ".//cac:WithholdingTaxTotal//cac:TaxSubtotal//cac:TaxCategory//cbc:TaxTypeCode", line_tree,
            ),
            "tax_percentage": float(tax_percentage) if tax_percentage else 0.0,
        }

    @api.model
    def _l10n_tr_import_line_discount(self, line_tree):
        discount_percentage = self._find_value(
            ".//cac:AllowanceCharge/cbc:MultiplierFactorNumeric",
            line_tree,
        )
        return float(discount_percentage) * 100 if discount_percentage else 0.0

    @api.model
    def _l10n_tr_resolve_invoice_lines(self, tree, invoice_values, move_type, logs):
        profile_id = self._l10n_tr_import_profile_id(tree)
        invoice_type = self._l10n_tr_import_invoice_type_code(tree)
        lines_nodes = tree.findall(".//cac:InvoiceLine", namespaces=UBL_NAMESPACES)
        if not lines_nodes:
            logs.append(_("No invoice lines were found in the document."))
            return

        # Pre-process data
        line_data = []
        for line_tree in lines_nodes:
            line_data.append(
                {
                    "default_code": self._find_value(".//cac:Item/cac:SellersItemIdentification/cbc:ID", line_tree),
                    "ctsp_number": self._find_value(".//cbc:RequiredCustomsID", line_tree),
                    "line_name": self._find_value(".//cac:Item/cbc:Description", line_tree),
                    "price_unit": self._find_value(".//cac:Price/cbc:PriceAmount", line_tree),
                    "discount_percentage": self._l10n_tr_import_line_discount(line_tree),
                    "qty": self._find_value(".//cbc:InvoicedQuantity", line_tree),
                    "tax_details": self._l10n_tr_import_tax_details(line_tree),
                },
            )
        product_ids_by_dc_ctsp = self._l10n_tr_find_product_id_by_default_code_or_ctsp(
            [
                (line["default_code"], line["ctsp_number"])
                for line in line_data
                if line["default_code"] or line["ctsp_number"]
            ],
        )

        tax_id_by_tax_details = self._l10n_tr_find_tax_id_by_tax_details(
            [(line["tax_details"]) for line in line_data if line["tax_details"]],
            profile_id,
            invoice_type,
            move_type,
        )

        # set line vals
        invoice_values["invoice_line_ids"] = []
        for i, data in enumerate(line_data):
            product_id = (
                product_ids_by_dc_ctsp["ctsp_numbers"].get(data["ctsp_number"], False)
                or product_ids_by_dc_ctsp["default_codes"].get(data["default_code"], False)
            )

            line_val = {
                "product_id": product_id.id if product_id else False,
                "price_unit": float(data["price_unit"] or 0),
                "quantity": float(data["qty"] or 0),
                "tax_ids": tax_id_by_tax_details[i]
                if tax_id_by_tax_details[i]
                else False,
                "discount": data["discount_percentage"],
            }
            if not product_id:
                line_val["name"] = data["line_name"]

            invoice_values["invoice_line_ids"].append(Command.create(line_val))

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # EXTENDS account_edi_ubl_cii
        # Adding custom decoder for Nilvera's TR1.2 UBL format

        if self._find_value(".//cbc:CustomizationID", tree) != "TR1.2":
            return super()._import_fill_invoice(invoice, tree, qty_factor)

        if qty_factor == -1:
            # TODO: Support credit note for UBL TR1.2
            return [_("Invoice/Bill return creation from XML is not supported for TR1.2 UBL format yet.")]

        logs = []
        invoice_values = {}

        # ==== Nilvera UUID ====
        if uuid_node := self._find_value(".//cbc:UUID", tree):
            invoice_values["l10n_tr_nilvera_uuid"] = uuid_node

        # ==== Process partner ====
        partner_id = self._l10n_tr_resolve_invoice_partner(tree, invoice.company_id, invoice_values, logs)

        # ==== Process Bank details ====
        bank_recipient = self.env.company.partner_id if invoice.is_inbound() else partner_id
        self._l10n_tr_resolve_bank_account(tree, bank_recipient, invoice_values, logs)

        # ==== Delivery Details ====
        self._l10n_tr_resolve_delivery_details(tree, invoice_values)

        # ==== Exemption Details ====
        self._l10n_tr_resolve_export_exemption(tree, invoice_values, logs)

        # ==== Basic invoice fields ====
        self._l10n_tr_resolve_basic_fields(tree, invoice_values, logs)

        # ==== Lines =====
        move_type = "sale" if invoice.is_inbound() else "purchase"
        self._l10n_tr_resolve_invoice_lines(tree, invoice_values, move_type, logs)

        invoice.write(invoice_values)

        if not invoice.currency_id.active:
            invoice.currency_id.active = True
            logs.append(_("The currency %s has been reactivated.", invoice.currency_id.name))
        return logs
