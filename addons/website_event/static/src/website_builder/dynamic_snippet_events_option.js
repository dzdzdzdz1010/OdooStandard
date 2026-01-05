import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOption extends BaseOptionComponent {
    static id = "dynamic_snippet_events_option";
    static template = "website_event.DynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetEventsOption"];

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetEventsOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
    }
}

registry.category("website-options").add(DynamicSnippetEventsOption.id, DynamicSnippetEventsOption);
