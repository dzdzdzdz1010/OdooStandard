import { useChildRef, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { PartnerAutoComplete } from "@partner_autocomplete/js/partner_autocomplete_component";

export class PartnerAutoCompleteCharField extends CharField {
    static template = "partner_autocomplete.PartnerAutoCompleteCharField";
    static components = {
        ...CharField.components,
        PartnerAutoComplete,
    };
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.partnerAutocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "", parse: (v) => this.parse(v), ref: this.inputRef});
    }

    async validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get sources() {
        return [
            {
                options: async (request, shouldSearchWorldWide) => {
                    if (await this.validateSearchTerm(request)) {
                        let queryCountryId = this.props.record.data?.country_id ? this.props.record.data.country_id.id : false;
                        if (shouldSearchWorldWide){
                        	queryCountryId = 0;
                        }
                        const suggestions = await this.partnerAutocomplete.autocomplete(request, queryCountryId);
                        return suggestions.map((suggestion) => ({
                            cssClass: "partner_autocomplete_dropdown_char",
                            data: suggestion,
                            label: suggestion.name,
                            onSelect: () => this.onSelectPartnerAutocompleteOption(suggestion),
                        }));
                    }
                    else {
                        return [];
                    }
                },
                optionSlot: "partnerOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        ];
    }

    async onSelectPartnerAutocompleteOption(option) {
        let data = await this.partnerAutocomplete.getCreateData(option);
        if (!data?.company) {
            return;
        }

        if (data.logo) {
            const logoField = this.props.record.resModel === 'res.partner' ? 'image_1920' : 'logo';
            data.company[logoField] = data.logo;
        }

<<<<<<< 77bfe416d08eefc720f12899490d3d39efacb74a
        // Save UNSPSC codes (tags)
        const unspsc_codes = data.company.unspsc_codes

||||||| 382d0dc38a66273e6eda3e5adc3122032d1f1c89
        // Format the many2one fields
        const many2oneFields = ['country_id', 'state_id', 'industry_id'];
        many2oneFields.forEach((field) => {
            if (data.company[field]) {
                data.company[field] = [data.company[field].id, data.company[field].display_name];
            }
        });

        // Save UNSPSC codes (tags)
        const unspsc_codes = data.company.unspsc_codes

=======
        // Format the many2one fields
        const many2oneFields = ['country_id', 'state_id', 'industry_id'];
        many2oneFields.forEach((field) => {
            if (data.company[field]) {
                data.company[field] = [data.company[field].id, data.company[field].display_name];
            }
        });

        const additionalData = {
            entity_type : data.company.entity_type,
            unspsc_codes : data.company.unspsc_codes,
        };
>>>>>>> f2964928489299e7c15610229545e2fec368a562
        // Delete useless fields before updating record
        data.company = this.partnerAutocomplete.removeUselessFields(data.company, Object.keys(this.props.record.fields));

        // Update record with retrieved values
        if (data.company.name) {
            await this.props.record.update({name: data.company.name});  // Needed otherwise name it is not saved
        }

<<<<<<< 77bfe416d08eefc720f12899490d3d39efacb74a
        // Add UNSPSC codes (tags)
        if (this.props.record.resModel === 'res.partner' && unspsc_codes && unspsc_codes.length !== 0) {
            // category id is fetched and then tags are created (many2many)
            const category_id = await this.orm.call("res.partner", "iap_partner_autocomplete_add_tags", [this.props.record.resId, unspsc_codes]);
            data.company['category_id'] = [[6, 0, category_id]];
||||||| 382d0dc38a66273e6eda3e5adc3122032d1f1c89
        // Add UNSPSC codes (tags)
        if (this.props.record.resModel === 'res.partner' && unspsc_codes && unspsc_codes.length !== 0) {
            // We must first save the record so that we can then create the tags (many2many)
            const saved = await this.props.record.save();
            if (saved){
                await this.props.record.load();
                await this.orm.call("res.partner", "iap_partner_autocomplete_add_tags", [this.props.record.resId, unspsc_codes]);
                await this.props.record.load();
            }
=======
        if (this.props.record.resModel === 'res.partner') {
                const saved = await this.props.record.save();
                if(saved && data.isEnrichAccessible) {
                    await this.orm.call("res.partner", "enrich_company_message_post", [this.props.record.resId, additionalData]);
                    this.props.record.load();
                }
>>>>>>> f2964928489299e7c15610229545e2fec368a562
        }
        await this.props.record.update(data.company);

        if (this.props.setDirty) {
            this.props.setDirty(false);
        }
    }
}

export const partnerAutoCompleteCharField = {
    ...charField,
    component: PartnerAutoCompleteCharField,
};

registry.category("fields").add("field_partner_autocomplete", partnerAutoCompleteCharField);
