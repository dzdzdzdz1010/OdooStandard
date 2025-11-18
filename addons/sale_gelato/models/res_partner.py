# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.sale_gelato import const


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _gelato_validate_delivery_address(self):
        """
        Check that all required order's delivery address fields are set and correct length.

        :return: An error message if the delivery address is incomplete or too long, None otherwise.
        :rtype: str | None
        """
        return (
            self._gelato_ensure_partner_address_is_complete()
            or self._gelato_check_partner_address_exceeds_length_limit()
        )

    def _gelato_ensure_partner_address_is_complete(self):
        """Ensure that all order's partner address fields required by Gelato are set.

        :return: An error message if the address is incomplete, None otherwise.
        :rtype: str | None
        """
        required_address_fields = ['city', 'country_id', 'email', 'name', 'street']
        if self.country_id.code not in const.COUNTRIES_WITHOUT_ZIPCODE:
            required_address_fields.append('zip')
        missing_fields = [
            self._fields[field_name]
            for field_name in required_address_fields if not self[field_name]
        ]
        if missing_fields:
            translated_field_names = [f._description_string(self.env) for f in missing_fields]
            return _(
                "The following required address fields are missing: %s",
                ", ".join(translated_field_names),
            )

    def _gelato_check_partner_address_exceeds_length_limit(self):
        """Check that the address fields are compliant with Gelato maximum character limit.

        :return: An error message if any address field exceeds the limit, None otherwise.
        :rtype: str | None
        """
        max_address_lengths = {'street': 35, 'street2': 35, 'city': 30, 'zip': 15, 'phone': 25}
        exceeding_fields = {}

        for field, limit in max_address_lengths.items():
            if self[field] and len(self[field]) > limit:
                field_name = self._fields[field]._description_string(self.env)
                exceeding_fields[field_name] = limit

        if exceeding_fields:
            message = ", ".join([
                f"{field_name} (Max {limit})" for field_name, limit in exceeding_fields.items()
            ])
            return _("The following address fields are exceeding the character limit: %s", message)

    def _gelato_prepare_address_payload(self):
        """Trim address fields according to maximum length allowed by Gelato."""
        first_name, last_name = payment_utils.split_partner_name(self.name)

        return {
            'companyName': (self.commercial_company_name or '')[:60],
            'firstName': (first_name or last_name)[:25],  # Gelato require a first name.
            'lastName': last_name[:25],
            'addressLine1': self.street,
            'addressLine2': self.street2,
            'state': self.state_id.code,
            'city': self.city,
            'postCode': self.zip,
            'country': self.country_id.code,
            'email': self.email,
            'phone': self.phone or ''
        }
