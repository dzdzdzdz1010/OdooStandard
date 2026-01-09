import { describe, expect, queryFirst, queryOne, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineWebsiteModels();

test("fill color preview shows the hover fill color in outline mode", async () => {
    await setupWebsiteBuilder(
        '<p><a href="https://test.com/" class="btn btn-outline-custom" >Link label</a></p>',
        { loadIframeBundles: true }
    );
    await contains(":iframe p > a").click();

    // Set a background color
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#0000FF']").click();

    expect(":iframe p > a").toHaveStyle(
        "background-color: rgba(0, 0, 0, 0); background-image: none",
        {
            message:
                "When not hovering, the button background should be transparent in outline mode",
        }
    );
    expect(":iframe p > a").toHaveStyle("background-color: rgb(0, 0, 255)", { inline: true });
    expect("[data-label=Fill] .o_we_color_preview").toHaveStyle(
        "background-color: rgb(0, 0, 255)",
        { inline: true, message: "The fill color preview should show the hover fill color" }
    );

    // Set a background gradient
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".gradient-tab").click();
    const gradientButton = queryFirst(".o_gradient_color_button");
    const gradient = gradientButton.dataset.color;
    await contains(gradientButton).click();

    expect(":iframe p > a").toHaveStyle(
        "background-color: rgba(0, 0, 0, 0); background-image: none",
        {
            message:
                "When not hovering, the button background should be transparent in outline mode",
        }
    );
    expect(":iframe p > a").toHaveStyle({ "background-image": gradient }, { inline: true });
    expect("[data-label=Fill] .o_we_color_preview").toHaveStyle(
        { "background-image": gradient },
        { inline: true, message: "The fill color preview should show the hover fill color" }
    );
});

test("defaults to btn-primary style when switching from link to custom type", async () => {
    await setupWebsiteBuilder(
        '<p><a href="#">Link</a><a href="#" class="btn btn-primary" >Button Primary</a></p>',
        {
            loadIframeBundles: true,
            // We need to test if it works with transitions because Bootstrap
            // adds a transition on "btn" and LinkStyleAction needs an instant
            // style change to work properly when switching from link to custom.
            enableIframeTransitions: true,
        }
    );

    const linkSelector = ":iframe p > a:contains('Link')";
    await contains(linkSelector).click();

    expect("[data-label=Type] .o-hb-select-toggle").toHaveText("Link");
    await contains("[data-label=Type] .o-hb-select-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    const buttonPrimaryStyles = getComputedStyle(
        queryOne(":iframe p > a:contains('Button Primary')")
    );

    expect(linkSelector).toHaveClass("btn btn-custom");
    expect(linkSelector).toHaveStyle(
        {
            "background-color": buttonPrimaryStyles.backgroundColor,
            border: buttonPrimaryStyles.border,
            color: buttonPrimaryStyles.color,
        },
        { inline: true }
    );
});

test("keep current style when switching from button", async () => {
    await setupWebsiteBuilder('<p><a href="#" class="btn btn-secondary">Button Secondary</a></p>', {
        loadIframeBundles: true,
    });

    const computedStyle = getComputedStyle(queryOne(":iframe p > a"));
    const buttonSecondaryStyles = {
        "background-color": computedStyle.backgroundColor,
        border: computedStyle.border,
        color: computedStyle.color,
    };
    await contains(":iframe p > a").click();

    expect("[data-label=Type] .o-hb-select-toggle").toHaveText("Button Secondary");
    await contains("[data-label=Type] .o-hb-select-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    expect(":iframe p > a").toHaveClass("btn btn-custom");
    expect(":iframe p > a").toHaveStyle(buttonSecondaryStyles, { inline: true });
});

test("remove style when switching back to link type", async () => {
    await setupWebsiteBuilder(
        `<p><a 
                href="#" class="btn btn-custom text-o-color-1" 
                style="color: rgb(0, 255, 0); background-color: rgb(0, 0, 255); background-image: linear-gradient(135deg, rgb(102, 153, 255) 0%, rgb(255, 51, 102) 100%); border-width: 4px; border-color: rgb(255, 0, 0); border-style: dotted;"
            >Link label</a></p>`,
        { loadIframeBundles: true }
    );

    await contains(":iframe p > a").click();

    expect("[data-label=Type] .o-hb-select-toggle").toHaveText("Custom");
    await contains("[data-label=Type] .o-hb-select-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Link')").click();

    expect(":iframe p > a").toHaveAttribute("class", "");
    expect(":iframe p > a").toHaveAttribute("style", "");
});
