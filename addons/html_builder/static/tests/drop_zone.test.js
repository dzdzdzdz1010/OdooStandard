import {
    setupHTMLBuilder,
    waitForEndOfOperation,
    confirmAddSnippet,
} from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const dropzone = (hovered = false) => {
    const highlightClass = hovered ? " o_dropzone_highlighted" : "";
    return `<div class="oe_drop_zone oe_insert${highlightClass}" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE"></div>`;
};

test("wrapper element has the 'DRAG BUILDING BLOCKS HERE' message", async () => {
    const { contentEl } = await setupHTMLBuilder("");
    expect(contentEl).toHaveAttribute("data-editor-message", "DRAG BUILDING BLOCKS HERE");
});

test("drop beside dropzone inserts the snippet", async () => {
    const { contentEl } = await setupHTMLBuilder();
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(contentEl.ownerDocument.body);
    // The dropzone is not hovered, so not highlighted.
    expect(contentEl).toHaveInnerHTML(dropzone());
    await drop();
    await confirmAddSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    await waitForEndOfOperation();
    expect(contentEl)
        .toHaveInnerHTML(`<section class="s_test" data-snippet="s_test" data-name="Test">
    <div class="test_a"></div>
    </section>`);
});

test("content snippets cannot be dropped next to elements inside oe_structure", async () => {
    const snippetContent = [
        `<div name="Image" data-oe-thumbnail="image.svg" data-oe-snippet-id="456">
            <img src="/web/image/test.png" data-snippet="s_image" alt="Test Image"/>
        </div>`,
    ];

    // This mimics the real dropzone selector for content snippets
    const dropzoneSelectors = [
        {
            selector: "img",
            dropNear: "p, h1, h2, h3",
            excludeNearParent: ".oe_structure",
        },
    ];

    const { getEditor } = await setupHTMLBuilder(
        `<div class="oe_structure"><h1>Title</h1><p>Paragraph</p></div>`,
        { snippetContent, dropzoneSelectors }
    );

    const editor = getEditor();
    const disableSnippetsPlugin = editor.plugins.find(
        (p) => p.constructor.id === "disableSnippets"
    );
    const setupEditorPlugin = editor.plugins.find(
        (p) => p.constructor.id === "setup_editor_plugin"
    );
    const dropzonePlugin = editor.plugins.find((p) => p.constructor.id === "dropzone");

    // Get drop areas using the plugin method that was fixed
    const editableAreaEls = setupEditorPlugin.getEditableAreas();
    const rootEl = dropzonePlugin.getDropRootElement();
    const dropAreasBySelector = disableSnippetsPlugin.getDropAreas(editableAreaEls, rootEl);

    // Find the drop areas for our image selector
    const imageDropAreas = dropAreasBySelector.find((item) => item.selector === "img");

    expect(imageDropAreas?.dropAreaEls || []).toHaveLength(0, {
        message: "Content snippets should not have drop zones next to h1/p inside .oe_structure",
    });
});
