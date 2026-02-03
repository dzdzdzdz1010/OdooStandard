from lxml import etree
from odoo import models


class AccountEdiXmlFacturxFrBasicwl(models.AbstractModel):
    _name = "account.edi.xml.facturx_fr_basicwl"
    _inherit = "account.edi.xml.cii_fr"
    _description = "Factur-X France (Basic WL)"

    """
    Factur-X is a PDF/A-3 with an embedded CII XML.

    The Basic WL profile uses the same French CII post-processing as the CIUS
    (mandatory notes, SIREN fix, electronic addresses, etc.). Only the Factur-X
    profile identifier differs.
    """

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_facturx_basicwl.xml"

    def _get_document_context_id(self):
        return "urn:factur-x.eu:1p0:basicwl"

    def _get_facturx_conformance_level(self):
        """Return the Factur-X PDF/A-3 conformance level."""
        return "BASIC WL"

    def _patch_facturx_pdfa3_metadata(self, metadata_content, xml_filename):
        """Patch the PDF/A-3 XMP metadata for Factur-X.

        We keep the shared QWeb template stable and update the variable values
        (conformance level + embedded XML filename) at the builder level.
        """

        ns = {'fx': 'urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#'}
        tree = etree.fromstring(metadata_content.encode('utf-8'))

        conformance_node = tree.find('.//fx:ConformanceLevel', namespaces=ns)
        if conformance_node is not None:
            conformance_node.text = self._get_facturx_conformance_level()

        filename_node = tree.find('.//fx:DocumentFileName', namespaces=ns)
        if filename_node is not None:
            filename_node.text = xml_filename

        return etree.tostring(tree, encoding='unicode')
