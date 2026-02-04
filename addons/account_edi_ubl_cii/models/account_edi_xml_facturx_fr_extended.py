from lxml import etree
from odoo import models


class AccountEdiXmlFacturxFrExtended(models.AbstractModel):
    _name = "account.edi.xml.facturx_fr_extended"
    _inherit = "account.edi.xml.cii_fr_extended"
    _description = "Factur-X France (Extended)"

    """
    Factur-X Extended profile.

    This builder reuses the French CIUS Extended CII generation and only overrides
    the Factur-X profile identifier (document context ID).

    Note: Factur-X extended URN is distinct from the French CTC extended URN
    ('urn.cpro.gouv.fr:1p0:extended-ctc-fr').
    """

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_facturx_extended.xml"

    def _get_document_context_id(self):
        return "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"

    def _get_facturx_conformance_level(self):
        """Return the Factur-X PDF/A-3 conformance level."""
        return "EXTENDED"

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
