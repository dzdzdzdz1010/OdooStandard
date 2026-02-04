from lxml import etree
from odoo import models


class AccountEdiXmlFacturxFrEn16931(models.AbstractModel):
    _name = "account.edi.xml.facturx_fr_en16931"
    _inherit = "account.edi.xml.cii_fr"
    _description = "Factur-X France (EN16931)"

    """
    Factur-X EN16931 profile.

    This builder reuses the French CIUS CII generation and only overrides the
    Factur-X profile identifier (document context ID).
    """

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_facturx_en16931.xml"

    def _get_document_context_id(self):
        return "urn:cen.eu:en16931:2017"

    def _get_facturx_conformance_level(self):
        """Return the Factur-X PDF/A-3 conformance level."""
        return "EN 16931"

    def _patch_facturx_pdfa3_metadata(self, metadata_content, xml_filename):
        """Patch the PDF/A-3 XMP metadata for Factur-X."""

        ns = {'fx': 'urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#'}
        tree = etree.fromstring(metadata_content.encode('utf-8'))

        conformance_node = tree.find('.//fx:ConformanceLevel', namespaces=ns)
        if conformance_node is not None:
            conformance_node.text = self._get_facturx_conformance_level()

        filename_node = tree.find('.//fx:DocumentFileName', namespaces=ns)
        if filename_node is not None:
            filename_node.text = xml_filename

        return etree.tostring(tree, encoding='unicode')
