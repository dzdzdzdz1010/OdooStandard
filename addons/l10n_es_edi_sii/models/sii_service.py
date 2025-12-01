import json

import requests

from odoo import fields, models
from odoo.tools import html_escape, zeep

from odoo.addons.certificate.tools import CertificateAdapter

EUSKADI_CIPHERS = "DEFAULT:!DH"

AEAT_BASE_URL = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/"
    "dep/aplicaciones/es/aeat/ssii_1_1/fact/ws"
)
AEAT_TEST_BASE_URL = "https://prewww1.aeat.es/wlpl/SSII-FACT/ws"

BIZKAIA_BASE_URL = "https://www.bizkaia.eus/ogasuna/sii/documentos"
BIZKAIA_TEST_BASE_URL = "https://pruapps.bizkaia.eus/SSII-FACT/ws"

GIPUZKOA_BASE_URL = "https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1"
GIPUZKOA_TEST_BASE_URL = "https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws"


class L10nEsSiiService(models.AbstractModel):
    _name = "l10n_es.sii.service"
    _description = "Spanish SII Service"

    def _send_sii_invoice(self, invoice, cancel=False):
        invoice.ensure_one()
        company = invoice.company_id

        # Clear previous error before retry
        if invoice.l10n_es_edi_sii_error:
            invoice.l10n_es_edi_sii_error = False

        # Certificate check
        if not company.l10n_es_sii_certificate_id:
            invoice.l10n_es_edi_sii_error = self.env._(
                "Please configure the certificate for SII."
            )
            return {invoice: {'blocking_level': 'error'}}

        # Tax agency check
        if not company.l10n_es_sii_tax_agency:
            invoice.l10n_es_edi_sii_error = self.env._(
                "Please specify a tax agency on your company for SII."
            )
            return {invoice: {'blocking_level': 'error'}}

        # Invoice configuration validation
        errors = invoice._l10n_es_sii_check_move_configuration()
        if errors:
            invoice.l10n_es_edi_sii_error = self.env._(
                "Invalid invoice configuration:<br/>%s",
                "<br/>".join(errors),
            )
            return {invoice: {'blocking_level': 'error'}}

        # Generate payload
        info_list = invoice._l10n_es_edi_get_invoices_info()

        # Call SII web service
        res = self._l10n_es_edi_call_web_service_sign(
            invoice, info_list, cancel=cancel
        )

        if res.get(invoice, {}).get('success'):
            invoice.l10n_es_edi_sii_state = 'sent'

            attachment = self.env['ir.attachment'].create({
                'type': 'binary',
                'name': f'sii_payload_{invoice.name or invoice.id}.json',
                'raw': json.dumps(info_list),
                'mimetype': 'application/json',
                'res_model': invoice._name,
                'res_id': invoice.id,
            })
            res[invoice]['attachment'] = attachment

            if cancel:
                invoice.l10n_es_edi_csv = False
                invoice.l10n_es_edi_sii_state = False
        else:
            # Error already written by the service layer
            invoice.l10n_es_edi_sii_state = 'to_send'

        return res

    def _l10n_es_edi_call_web_service_sign(self, invoice, info_list, cancel=False):
        company = invoice.company_id

        # All are sharing the same value.
        csv_number = invoice.l10n_es_edi_csv

        # Set registration date
        if not invoice.l10n_es_registration_date:
            invoice.l10n_es_registration_date = fields.Date.context_today(self)

        # === Call the web service ===

        # Get connection data.
        l10n_es_sii_tax_agency = company.l10n_es_sii_tax_agency
        SERVICE_CONFIG_MAP = {
            'aeat': self._l10n_es_edi_web_service_aeat_vals,
            'bizkaia': self._l10n_es_edi_web_service_bizkaia_vals,
            'gipuzkoa': self._l10n_es_edi_web_service_gipuzkoa_vals,
        }
        connection_vals = SERVICE_CONFIG_MAP[l10n_es_sii_tax_agency](invoice)

        header = {
            'IDVersionSii': '1.1',
            'Titular': {
                'NombreRazon': company.name[:120],
                'NIF': company.vat[2:] if company.vat.startswith('ES') else company.vat,
            },
            'TipoComunicacion': 'A1' if csv_number else 'A0',
        }

        session = requests.Session()
        session.cert = company.l10n_es_sii_certificate_id
        session.mount('https://', CertificateAdapter(ciphers=EUSKADI_CIPHERS))

        client = zeep.Client(connection_vals['url'], operation_timeout=60, timeout=60, session=session)

        if invoice.is_sale_document():
            service_name = 'SuministroFactEmitidas'
        else:
            service_name = 'SuministroFactRecibidas'
        if company.l10n_es_sii_test_env and not connection_vals.get('test_url'):
            service_name += 'Pruebas'

        # Establish the connection.
        serv = client.bind('siiService', service_name)
        if company.l10n_es_sii_test_env and connection_vals.get('test_url'):
            serv._binding_options['address'] = connection_vals['test_url']

        error_msg = None
        try:
            if cancel:
                if invoice.is_sale_document():
                    res = serv.AnulacionLRFacturasEmitidas(header, info_list)
                else:
                    res = serv.AnulacionLRFacturasRecibidas(header, info_list)
            else:
                if invoice.is_sale_document():
                    res = serv.SuministroLRFacturasEmitidas(header, info_list)
                else:
                    res = serv.SuministroLRFacturasRecibidas(header, info_list)
        except requests.exceptions.SSLError:
            error_msg = self.env._("The SSL certificate could not be validated.")
        except (zeep.exceptions.Error, requests.exceptions.ConnectionError) as error:
            error_msg = self.env._("Networking error:\n%s", error)
        except Exception as error:  # noqa: BLE001
            error_msg = str(error)

        if error_msg:
            return {
                invoice: {
                    'error': error_msg,
                    'blocking_level': 'warning',
            }
        }

        # Process response.
        if not res or not res.RespuestaLinea:
            return {
                invoice: {
                    'error': self.env._("The web service is not responding"),
                    'blocking_level': 'warning',
                }
            }

        resp_state = res["EstadoEnvio"]
        l10n_es_edi_csv = res['CSV']

        if resp_state == 'Correcto':
            invoice.write({'l10n_es_edi_csv': l10n_es_edi_csv})
            return {
                invoice: {'success': True}
            }

        results = {}
        for respl in res.RespuestaLinea:
            invoice_number = respl.IDFactura.NumSerieFacturaEmisor

            # Retrieve the corresponding invoice.
            # Note: ref can be the same for different partners but there is no enough information on the response
            # to match the partner.

            # Note: Invoices are batched per move_type.
            if invoice.is_sale_document():
                inv = invoice.filtered(lambda x: x.name[:60] == invoice_number)
            else:
                # 'ref' can be the same for different partners.
                candidates = invoice.filtered(lambda x: x.ref[:60] == invoice_number)
                if len(candidates) > 1:
                    respl_partner_info = respl.IDFactura.IDEmisorFactura
                    inv = None
                    for candidate in candidates:
                        partner = candidate.commercial_partner_id
                        if candidate._l10n_es_is_dua():
                            partner = candidate.company_id.partner_id
                        partner_info = partner._l10n_es_edi_get_partner_info()
                        if partner_info.get('NIF') and partner_info['NIF'] == respl_partner_info.NIF:
                            inv = candidate
                            break
                        if (
                            partner_info.get('IDOtro')
                            and respl_partner_info['IDOtro']
                            and all(respl_partner_info['IDOtro'][k] == v for k, v in partner_info['IDOtro'].items())
                        ):
                            inv = candidate
                            break

                    if not inv:
                        # This case shouldn't happen and means there is something wrong in this code. However, we can't
                        # raise anything since the document has already been approved by the government. The result
                        # will only be a badly logged message into the chatter so, not a big deal.
                        inv = candidates[0]
                else:
                    inv = candidates

            resp_line_state = respl.EstadoRegistro
            respl_dict = dict(respl)
            if resp_line_state in ('Correcto', 'AceptadoConErrores'):
                inv.l10n_es_edi_csv = l10n_es_edi_csv
                results[inv] = {'success': True}
                if resp_line_state == 'AceptadoConErrores':
                    inv.message_post(body=self.env._("This was accepted with errors: ") + html_escape(respl.DescripcionErrorRegistro))
            elif (
                (respl_dict.get('RegistroDuplicado') and respl.RegistroDuplicado.EstadoRegistro == 'Correcta')
                or
                (cancel and respl_dict.get('CodigoErrorRegistro') == 3001)
            ):
                results[inv] = {'success': True}
                inv.message_post(body=self.env._("We saw that this invoice was sent correctly before, but we did not treat "
                                        "the response.  Make sure it is not because of a wrong configuration."))

            elif respl.CodigoErrorRegistro == 1117 and not self.env.context.get('error_1117'):
                return self.with_context(error_1117=True)._l10n_es_edi_sii_post_invoice(invoice)

            else:
                results[inv] = {
                    'error': self.env._("[%(error_code)s] %(error_message)s", error_code=respl.CodigoErrorRegistro, error_message=respl.DescripcionErrorRegistro),
                    'blocking_level': 'error',
                }

        return results

    def _l10n_es_edi_web_service_aeat_vals(self, invoice):
        if invoice.is_sale_document():
            return {
                'url': f'{AEAT_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{AEAT_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{AEAT_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{AEAT_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }

    def _l10n_es_edi_web_service_bizkaia_vals(self, invoice):
        if invoice.is_sale_document():
            return {
                'url': f'{BIZKAIA_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{BIZKAIA_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{BIZKAIA_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{BIZKAIA_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }

    def _l10n_es_edi_web_service_gipuzkoa_vals(self, invoice):
        if invoice.is_sale_document():
            return {
                'url': f'{GIPUZKOA_BASE_URL}/SuministroFactEmitidas.wsdl',
                'test_url': f'{GIPUZKOA_TEST_BASE_URL}/fe/SiiFactFEV1SOAP',
            }
        return {
            'url': f'{GIPUZKOA_BASE_URL}/SuministroFactRecibidas.wsdl',
            'test_url': f'{GIPUZKOA_TEST_BASE_URL}/fr/SiiFactFRV1SOAP',
        }
