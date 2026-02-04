import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { animationFrame, click, queryFirst } from "@odoo/hoot-dom";
import { fonts } from "@html_editor/utils/fonts";

defineWebsiteModels();

test("List Group Snippet", async () => {
    patchWithCleanup(fonts, {
        computeFonts() {
            super.computeFonts();
            this.fontIcons[0].cssData.unshift({
                selector: ".fa-custom::before",
                css: 'content: "custom";',
                names: ["fa-custom"],
            });
        },
    });

    await setupWebsiteBuilderWithSnippet("s_list_group", {
        styleContent: `
            .s_list_group {
                --s_list_group-icon-content: "\\f00c";
                --s_list_group-icon-color: #714B67;
                --s_list_group-icon-bg: #dfdfdf;
                padding: 1em 0;
            }

            .s_list_group ul {
                list-style: none;
                padding-left: 0;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }

            .s_list_group ul li {
                position: relative;
                padding-left: 2em;
            }

            .s_list_group ul li:not(.oe-nested)::before {
                content: var(--s_list_group-icon-content);
                color: var(--s_list_group-icon-color);
                background: var(--s_list_group-icon-bg);
                font-family: "FontAwesome";
                position: absolute;
                left: 0;
                width: 1.5em;
                display: inline-flex;
                justify-content: center;
                align-items: center;
                border-radius: 50%;
            }
        `,
    });
    await contains(":iframe .s_list_group").click();
    await click(".options-container div[data-label='Color'] button");
    await animationFrame();
    await click(".o_popover button[data-color='#FF0000']");
    await animationFrame();
    const el = queryFirst(":iframe .s_list_group li");
    expect(getComputedStyle(el).getPropertyValue("--s_list_group-icon-color").trim()).toBe("#FF0000");
    await click(".options-container div[data-label='Background'] button");
    await animationFrame();
    await click(".popover button.gradient-tab");
    await animationFrame();
    await click(".o_colorpicker_sections button");
    await animationFrame();
    expect(getComputedStyle(el).getPropertyValue("--s_list_group-icon-bg").trim()).toBe(
        "linear-gradient(135deg,rgb(255,204,51) 0%,rgb(226,51,255) 100%)"
    );
    await click(".options-container button[data-action-id='replaceListIcon']");
    await animationFrame();
    await click(".modal-dialog .fa-custom");
    await animationFrame();
    const iconContent = getComputedStyle(el).getPropertyValue("--s_list_group-icon-content").trim();
    expect(iconContent).toMatch(/^["']custom["']$/);
});
