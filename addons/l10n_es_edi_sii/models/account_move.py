# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import math

from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_is_required = fields.Boolean(
        string="Is the Spanish EDI needed",
        compute='_compute_l10n_es_edi_is_required'
    )
    l10n_es_edi_csv = fields.Char(string="CSV return code", copy=False, tracking=True)
    # Technical field to keep the date the invoice was sent the first time as
    # the date the invoice was registered into the system.
    l10n_es_registration_date = fields.Date(
        string="Registration Date", copy=False,
    )
    l10n_es_edi_sii_state = fields.Selection(
        [
            ('to_send', "To Send"),
            ('sent', "Sent"),
        ],
        string="Spain SII Status",
        compute="_compute_l10n_es_edi_sii_status",
        copy=False,
        tracking=True,
    )
    l10n_es_edi_sii_error = fields.Html(readonly=True, copy=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_es_edi_is_required(self):
        for move in self:
            has_tax = True
            # Check it is not an importation invoice (which will be report through the DUA invoice)
            if move.is_purchase_document():
                taxes = move.invoice_line_ids.tax_ids
                has_tax = any(t.l10n_es_type and t.l10n_es_type != 'ignore' for t in taxes)
            move.l10n_es_edi_is_required = move.is_invoice() \
                                           and move.country_code == 'ES' \
                                           and move.company_id.l10n_es_sii_tax_agency \
                                           and has_tax

    @api.depends('state', 'l10n_es_edi_is_required')
    def _compute_l10n_es_edi_sii_status(self):
        for record in self:
            record.l10n_es_edi_sii_state = 'to_send' if record.l10n_es_edi_is_required else False

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())

    def _l10n_es_prepare_tax_details(self, filter_to_apply=None, filter_invl_to_apply=None, grouping_key_generator=None):
        return self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=filter_invl_to_apply,
            filter_tax_values_to_apply=filter_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

    def button_draft(self):
        self.filtered(lambda m: m.l10n_es_edi_sii_state == 'sent').l10n_es_edi_sii_state = False
        return super().button_draft()

    def action_l10n_es_send_sii(self):
        self.ensure_one()
        self.env['l10n_es.sii.service']._send_sii_invoice(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        }

    def _l10n_es_sii_check_move_configuration(self):
        self.ensure_one()
        errors = []

        if not self.company_id.vat:
            errors.append(self.env._("VAT number is missing on company %s.", self.company_id.display_name))

        lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_subsection', 'line_note')
        )

        total_taxes = lines.mapped('tax_ids').flatten_taxes_hierarchy()
        for line in lines:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            l10n_types = taxes.mapped('l10n_es_type')

            recargo_count = l10n_types.count('recargo')
            retention_count = l10n_types.count('retencion')
            sujeto_count = l10n_types.count('sujeto')
            no_sujeto_count = l10n_types.count('no_sujeto')
            no_sujeto_loc_count = l10n_types.count('no_sujeto_loc')
            if retention_count > 1:
                errors.append(self.env._("Line %s should only have one retention tax.", line.display_name))
            if recargo_count > 1:
                errors.append(self.env._("Line %s should only have one recargo tax.", line.display_name))
            if sujeto_count > 1:
                errors.append(self.env._("Line %s should only have one sujeto tax.", line.display_name))
            if no_sujeto_count > 1:
                errors.append(self.env._("Line %s should only have one no sujeto tax.", line.display_name))
            if no_sujeto_loc_count > 1:
                errors.append(self.env._("Line %s should only have one no sujeto (localizations) tax.", line.display_name))
            if sujeto_count + no_sujeto_loc_count + no_sujeto_count > 1:
                errors.append(self.env._("Line %s should only have one main tax.", line.display_name))

        if (
            self.is_outbound()
            and self.commercial_partner_id._l10n_es_is_foreign()
            and total_taxes
            and not any(t.tax_scope for t in total_taxes)
        ):
            errors.append(
                self.env._("In case of a foreign customer, you need to configure the tax scope on taxes:\n%s",
                           "\n".join(total_taxes.mapped('name')))
            )
        return errors

    def _l10n_es_edi_get_invoices_info(self):
        info_list = []
        com_partner = self.commercial_partner_id
        is_simplified = self.l10n_es_is_simplified

        info = {
            'PeriodoLiquidacion': {
                'Ejercicio': str(self.date.year),
                'Periodo': str(self.date.month).zfill(2),
            },
            'IDFactura': {
                'FechaExpedicionFacturaEmisor': self.invoice_date.strftime('%d-%m-%Y'),
            },
        }

        if self.is_sale_document():
            invoice_node = info['FacturaExpedida'] = {}
        else:
            invoice_node = info['FacturaRecibida'] = {}

        # === Partner ===

        partner_info = com_partner._l10n_es_edi_get_partner_info()

        # === Invoice ===

        if self.delivery_date and self.delivery_date != self.invoice_date:
            invoice_node['FechaOperacion'] = self.delivery_date.strftime('%d-%m-%Y')
        invoice_node['DescripcionOperacion'] = self.invoice_origin[:500] if self.invoice_origin else 'manual'
        reagyp = self.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_type == 'sujeto_agricultura')
        if self.is_sale_document():
            nif = self.company_id.vat[2:] if self.company_id.vat.startswith('ES') else self.company_id.vat
            info['IDFactura']['IDEmisorFactura'] = {'NIF': nif}
            info['IDFactura']['NumSerieFacturaEmisor'] = self.name[:60]
            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120],
                }
            invoice_node['ClaveRegimenEspecialOTrascendencia'] = self.invoice_line_ids.tax_ids._l10n_es_get_regime_code()
        else:
            if self._l10n_es_is_dua():
                partner = self.company_id.partner_id
                partner_info = partner._l10n_es_edi_get_partner_info()
            info['IDFactura']['IDEmisorFactura'] = partner_info
            # In case of cancel
            info["IDFactura"]["IDEmisorFactura"].update(
                {"NombreRazon": com_partner.name[0:120]}
            )
            info["IDFactura"]["NumSerieFacturaEmisor"] = (self.ref or "")[:60]
            if not is_simplified:
                invoice_node['Contraparte'] = {
                    **partner_info,
                    'NombreRazon': com_partner.name[:120],
                }

            if self.l10n_es_registration_date:
                invoice_node['FechaRegContable'] = self.l10n_es_registration_date.strftime('%d-%m-%Y')
            else:
                invoice_node['FechaRegContable'] = fields.Date.context_today(self).strftime('%d-%m-%Y')

            mod_303_10 = self.env.ref('l10n_es.mod_303_casilla_10_balance')._get_matching_tags()
            mod_303_11 = self.env.ref('l10n_es.mod_303_casilla_11_balance')._get_matching_tags()
            tax_tags = self.invoice_line_ids.tax_ids.repartition_line_ids.tag_ids
            intracom = bool(tax_tags & (mod_303_10 + mod_303_11))
            if intracom:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '09'
            elif reagyp:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '02'
            else:
                invoice_node['ClaveRegimenEspecialOTrascendencia'] = '01'

        if self.move_type == 'out_invoice':
            invoice_node['TipoFactura'] = 'F2' if is_simplified else 'F1'
        elif self.move_type == 'out_refund':
            invoice_node['TipoFactura'] = 'R5' if is_simplified else 'R1'
            invoice_node['TipoRectificativa'] = 'I'
        elif self.move_type == 'in_invoice':
            if reagyp:
                invoice_node['TipoFactura'] = 'F6'
            elif self._l10n_es_is_dua():
                invoice_node['TipoFactura'] = 'F5'
            else:
                invoice_node['TipoFactura'] = 'F1'
        elif self.move_type == 'in_refund':
            invoice_node['TipoFactura'] = 'R4'
            invoice_node['TipoRectificativa'] = 'I'

        # === Taxes ===

        sign = -1 if self.move_type in ('out_refund', 'in_refund') else 1

        if self.is_sale_document():
            # Customer invoices
            if not com_partner._l10n_es_is_foreign() or is_simplified:
                tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info()
                invoice_node['TipoDesglose'] = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}

                invoice_node['ImporteTotal'] = float_round(sign * (
                    tax_details_info_vals['tax_details']['base_amount']
                    + tax_details_info_vals['tax_details']['tax_amount']
                    - tax_details_info_vals['tax_amount_retention']
                ), 2)
            else:
                tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
                )
                tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
                )

                if tax_details_info_service_vals['tax_details_info']:
                    invoice_node.setdefault('TipoDesglose', {})
                    invoice_node['TipoDesglose'].setdefault('DesgloseTipoOperacion', {})
                    invoice_node['TipoDesglose']['DesgloseTipoOperacion']['PrestacionServicios'] = tax_details_info_service_vals['tax_details_info']
                if tax_details_info_consu_vals['tax_details_info']:
                    invoice_node.setdefault('TipoDesglose', {})
                    invoice_node['TipoDesglose'].setdefault('DesgloseTipoOperacion', {})
                    invoice_node['TipoDesglose']['DesgloseTipoOperacion']['Entrega'] = tax_details_info_consu_vals['tax_details_info']

                invoice_node['ImporteTotal'] = float_round(sign * (
                    tax_details_info_service_vals['tax_details']['base_amount']
                    + tax_details_info_service_vals['tax_details']['tax_amount']
                    - tax_details_info_service_vals['tax_amount_retention']
                    + tax_details_info_consu_vals['tax_details']['base_amount']
                    + tax_details_info_consu_vals['tax_details']['tax_amount']
                    - tax_details_info_consu_vals['tax_amount_retention']
                ), 2)

        else:
            # Vendor bills

            tax_details_info_isp_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
            )
            tax_details_info_other_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                filter_invl_to_apply=lambda x: not any(t for t in x.tax_ids if t.l10n_es_type == 'sujeto_isp'),
            )

            invoice_node['DesgloseFactura'] = {}
            if tax_details_info_isp_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['InversionSujetoPasivo'] = tax_details_info_isp_vals['tax_details_info']
            if tax_details_info_other_vals['tax_details_info']:
                invoice_node['DesgloseFactura']['DesgloseIVA'] = tax_details_info_other_vals['tax_details_info']

            if self._l10n_es_is_dua() or any(t.l10n_es_type == 'ignore' for t in self.invoice_line_ids.tax_ids):
                invoice_node['ImporteTotal'] = float_round(sign * (
                        tax_details_info_isp_vals['tax_details']['base_amount']
                        + tax_details_info_isp_vals['tax_details']['tax_amount']
                        + tax_details_info_other_vals['tax_details']['base_amount']
                        + tax_details_info_other_vals['tax_details']['tax_amount']
                ), 2)
            else:  # Intra-community -100 repartition line needs to be taken into account
                invoice_node['ImporteTotal'] = float_round(-self.amount_total_signed
                                                     - sign * tax_details_info_isp_vals['tax_amount_retention']
                                                     - sign * tax_details_info_other_vals['tax_amount_retention'], 2)

            invoice_node['CuotaDeducible'] = float_round(sign * (
                tax_details_info_isp_vals['tax_amount_deductible']
                + tax_details_info_other_vals['tax_amount_deductible']
            ), 2)

        info_list.append(info)
        return info_list

    def _l10n_es_edi_get_invoices_tax_details_info(self, filter_invl_to_apply=None):

        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        def filter_to_apply(base_line, tax_data):
            # For intra-community, we do not take into account the negative repartition line
            return (
                not tax_data['is_reverse_charge']
                and tax_data['tax'].amount != -100.0
                and tax_data['tax'].l10n_es_type != 'ignore'
            )

        def full_filter_invl_to_apply(invoice_line):
            if all(t == 'ignore' for t in invoice_line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type')):
                return False
            return filter_invl_to_apply(invoice_line) if filter_invl_to_apply else True

        tax_details = self._l10n_es_prepare_tax_details(
            grouping_key_generator=grouping_key_generator,
            filter_invl_to_apply=full_filter_invl_to_apply,
            filter_to_apply=filter_to_apply,
        )
        sign = -1 if self.is_refund() else 1

        tax_details_info = defaultdict(dict)

        # Detect for which is the main tax for 'recargo'. Since only a single combination tax + recargo is allowed
        # on the same invoice, this can be deduced globally.

        # Mapping between main tax and recargo tax details
        # structure: {("l10n_es_type" of the main tax, amount of the main tax): {'tax_amount': float, 'applied_tax_amount': float}}
        # dict of keys: tuple ("l10n_es_type" of the main tax, amount of the main tax)
        #       values: dict of float
        recargo_tax_details = defaultdict(lambda: defaultdict(float))
        for base_line in tax_details['base_lines']:
            line = base_line['record']
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_tax = taxes.filtered(lambda t: t.l10n_es_type == 'recargo')[:1]
            if recargo_tax and taxes:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                aggregated_values = tax_details['tax_details_per_record'][line]
                recargo_values = next(iter(
                    values
                    for values in aggregated_values['tax_details'].values()
                    if (
                        values['grouping_key']
                        and values['grouping_key']['l10n_es_type'] == recargo_tax.l10n_es_type
                        and values['grouping_key']['applied_tax_amount'] == recargo_tax.amount
                    )
                ))
                recargo_tax_details[recargo_main_tax.l10n_es_type, recargo_main_tax.amount]['tax_amount'] += recargo_values['tax_amount']
                recargo_tax_details[recargo_main_tax.l10n_es_type, recargo_main_tax.amount]['applied_tax_amount'] = recargo_values['applied_tax_amount']

        tax_amount_deductible = 0.0
        tax_amount_retention = 0.0
        base_amount_not_subject = 0.0
        base_amount_not_subject_loc = 0.0
        tax_subject_info_list = []
        tax_subject_isp_info_list = []
        for tax_values in tax_details['tax_details'].values():
            recargo = recargo_tax_details.get((tax_values['l10n_es_type'], tax_values['applied_tax_amount']))
            if self.is_sale_document():
                # Customer invoices

                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp'):
                    tax_amount_deductible += tax_values['tax_amount']

                    base_amount = sign * tax_values['base_amount']
                    tax_info = {
                        'TipoImpositivo': tax_values['applied_tax_amount'],
                        'BaseImponible': float_round(base_amount, 2),
                        'CuotaRepercutida': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                    }

                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']

                    if tax_values['l10n_es_type'] == 'sujeto':
                        tax_subject_info_list.append(tax_info)
                    else:
                        tax_subject_isp_info_list.append(tax_info)

                elif tax_values['l10n_es_type'] == 'exento':
                    tax_details_info['Sujeta'].setdefault('Exenta', {'DetalleExenta': []})
                    tax_details_info['Sujeta']['Exenta']['DetalleExenta'].append({
                        'BaseImponible': float_round(sign * tax_values['base_amount'], 2),
                        'CausaExencion': tax_values['l10n_es_exempt_reason'],
                    })
                elif tax_values['l10n_es_type'] == 'retencion':
                    tax_amount_retention += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto':
                    base_amount_not_subject += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                    base_amount_not_subject_loc += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'ignore':
                    continue

            else:
                # Vendor bills
                if tax_values['l10n_es_type'] in ('sujeto', 'sujeto_isp', 'no_sujeto', 'no_sujeto_loc', 'dua'):
                    tax_amount_deductible += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'retencion':
                    tax_amount_retention += tax_values['tax_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto':
                    base_amount_not_subject += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'no_sujeto_loc':
                    base_amount_not_subject_loc += tax_values['base_amount']
                elif tax_values['l10n_es_type'] == 'ignore':
                    continue

                if tax_values['l10n_es_type'] not in ['retencion', 'recargo']:  # = in sujeto/sujeto_isp/no_deducible
                    base_amount = sign * tax_values['base_amount']
                    tax_details_info.setdefault('DetalleIVA', [])
                    tax_info = {
                        'BaseImponible': float_round(base_amount, 2),
                    }
                    if tax_values['l10n_es_type'] == 'sujeto_agricultura':
                        tax_info.update({
                            'PorcentCompensacionREAGYP': tax_values['applied_tax_amount'],
                            'ImporteCompensacionREAGYP': round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                        })
                    elif tax_values['applied_tax_amount'] > 0.0:
                        tax_info.update({
                            'TipoImpositivo': tax_values['applied_tax_amount'],
                            'CuotaSoportada': float_round(math.copysign(tax_values['tax_amount'], base_amount), 2),
                        })
                    if tax_values['l10n_es_bien_inversion']:
                        tax_info['BienInversion'] = 'S'
                    if recargo:
                        tax_info['CuotaRecargoEquivalencia'] = float_round(sign * recargo['tax_amount'], 2)
                        tax_info['TipoRecargoEquivalencia'] = recargo['applied_tax_amount']
                    tax_details_info['DetalleIVA'].append(tax_info)

        if tax_subject_isp_info_list and not tax_subject_info_list:  # Only for sale_invoices
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S2'}
        elif not tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S1'}
        elif tax_subject_isp_info_list and tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'] = {'TipoNoExenta': 'S3'}

        if tax_subject_info_list:
            tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_info_list
        if tax_subject_isp_info_list:
            tax_details_info['Sujeta']['NoExenta'].setdefault('DesgloseIVA', {})
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA'].setdefault('DetalleIVA', [])
            tax_details_info['Sujeta']['NoExenta']['DesgloseIVA']['DetalleIVA'] += tax_subject_isp_info_list

        if not self.company_id.currency_id.is_zero(base_amount_not_subject) and self.is_sale_document():
            tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = float_round(sign * base_amount_not_subject, 2)
        if not self.company_id.currency_id.is_zero(base_amount_not_subject_loc) and self.is_sale_document():
            tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = float_round(sign * base_amount_not_subject_loc, 2)
        if not tax_details_info and self.is_sale_document():
            if any(t['l10n_es_type'] == 'no_sujeto' for t in tax_details['tax_details'].values()):
                tax_details_info['NoSujeta']['ImportePorArticulos7_14_Otros'] = 0
            if any(t['l10n_es_type'] == 'no_sujeto_loc' for t in tax_details['tax_details'].values()):
                tax_details_info['NoSujeta']['ImporteTAIReglasLocalizacion'] = 0

        return {
            'tax_details_info': tax_details_info,
            'tax_details': tax_details,
            'tax_amount_deductible': tax_amount_deductible,
            'tax_amount_retention': tax_amount_retention,
            'base_amount_not_subject': base_amount_not_subject,
            'S1_list': tax_subject_info_list,  # TBAI has separate sections for S1 and S2
            'S2_list': tax_subject_isp_info_list,  # TBAI has separate sections for S1 and S2
        }
