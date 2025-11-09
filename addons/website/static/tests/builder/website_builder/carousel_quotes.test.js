import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { getDragMoveHelper } from "@html_builder/../tests/helpers";

defineWebsiteModels();

const SELECTORS = {
    carousel: ".s_quotes_carousel",
    slide: ".carousel-item .carousel-slide",
    blockquote: ".carousel-item blockquote",
    indicators: ".carousel-indicators",
};

async function changeLayout(numberOfElements) {
    await contains("[data-label='Layout'] .dropdown-toggle").click();
    await contains(
        `.o-overlay-item [data-action-id="updateQuotesCarouselLayout"]:nth-child(${numberOfElements})`
    ).click();
}

async function changeScrollMode(mode) {
    const index = mode === "single" ? 2 : 1;
    await contains(
        `[data-label="Scrolling Mode"] [data-action-id="updateQuotesCarouselLayout"]:nth-child(${index})`
    ).click();
}

function checkDatasetIndex(carouselSlideEls) {
    carouselSlideEls.forEach((carouselSlideEl, index) => {
        expect(carouselSlideEl.dataset.index).toBe(index.toString());
    });
}

function isIndicatorHidden(editableEl) {
    const indicatorContainerEl = editableEl.querySelector(".indicators-container");
    return indicatorContainerEl && indicatorContainerEl.classList.contains("d-none");
}

function expectWidth(element, count) {
    const blockquoteEl = element.querySelector("blockquote");
    expect(blockquoteEl).toHaveClass(`w-${Math.min((1 + count) * 25, 100)}`);
}

function isSingleMode(carouselEl, count) {
    const expectedStyle = `${100 / count}%`;
    return (
        carouselEl.classList.contains("o_carousel_multi_items") &&
        carouselEl.style.getPropertyValue("--o-carousel-item-width-percentage") === expectedStyle
    );
}

async function clickAddSlideButton(waitSidebarUpdated) {
    await contains("[data-container-title^='Slide'] [title='Add Slide']").click();
    await waitSidebarUpdated();
}

function assertAllMode(editableEl, count) {
    const carouselEl = editableEl.querySelector(SELECTORS.carousel);
    expect(isSingleMode(carouselEl, count)).toBe(false);
    const rowEls = editableEl.querySelectorAll(".carousel-item .row");
    expect(rowEls[0].querySelectorAll(".carousel-slide").length).toBe(count);
    const carouselSlideEls = carouselEl.querySelectorAll(SELECTORS.slide);
    expectWidth(carouselSlideEls[0], count);
    expect(isIndicatorHidden(editableEl)).toBe(false);
    checkDatasetIndex(carouselSlideEls);
}

function assertSingleMode(editableEl, count) {
    const carouselEl = editableEl.querySelector(SELECTORS.carousel);
    expect(isSingleMode(carouselEl, count)).toBe(true);
    const carouselItemEls = carouselEl.querySelectorAll(".carousel-item");
    expect(carouselItemEls).toHaveClass("carousel-slide");
    expect(carouselItemEls[0]).toHaveClass("active");
    expect(carouselItemEls[0]).toHaveAttribute("data-index", "0");
    expectWidth(carouselItemEls[0], count);
    expect(isIndicatorHidden(editableEl)).toBe(true);
    checkDatasetIndex(carouselItemEls);
}

async function testSlideReorder(editableEl) {
    await contains(`:iframe ${SELECTORS.blockquote}`).click();
    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    await moveTo(`:iframe ${SELECTORS.carousel} .carousel-item .row:last-child`);
    await drop(getDragMoveHelper());
    checkDatasetIndex(editableEl.querySelectorAll(SELECTORS.slide));
    await contains(".overlay .o-we-toolbar button[title='Move down']").click();
    checkDatasetIndex(editableEl.querySelectorAll(SELECTORS.slide));
}

async function clickToolbarActionAndAssert(assertLayoutFunction, editableEl, title, count) {
    await contains(`.overlay .o-we-toolbar button[title="${title}"]`).click();
    assertLayoutFunction(editableEl, count);
}

async function testQuoteCarousel(snippet) {
    const { getEditableContent, waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet(
        snippet
    );
    const editableEl = getEditableContent();
    await contains(`:iframe ${SELECTORS.carousel}_wrapper`).click();
    expect("div[data-label='Content Width']").toHaveCount(1);
    for (let elemenCount = 4; elemenCount > 1; elemenCount--) {
        await changeLayout(elemenCount);
        assertAllMode(editableEl, elemenCount);
        await changeScrollMode("single");
        assertSingleMode(editableEl, elemenCount);
        await changeScrollMode("all");
    }
    await testSlideReorder(editableEl);
    await clickToolbarActionAndAssert(assertAllMode, editableEl, "Remove", 2);
    await clickToolbarActionAndAssert(assertAllMode, editableEl, "Duplicate", 2);
    await changeScrollMode("single");
    await contains("[data-container-title^='Slide'] button[data-action-value='last']").click();
    const carouselSlideEls = editableEl.querySelectorAll(".carousel-slide");
    expect(carouselSlideEls[0]).toHaveClass("active");
    await changeScrollMode("all");
    await clickAddSlideButton(waitSidebarUpdated);
    await changeLayout(1);
    await contains(`:iframe ${SELECTORS.blockquote}`).click();
    await clickAddSlideButton(waitSidebarUpdated);
    const indicatorButtons = editableEl.querySelectorAll(`${SELECTORS.indicators} button`);
    expect(indicatorButtons.length).toBe(7);
}

test("Quote carousel layout and it's related options test", async () => {
    await testQuoteCarousel("s_quotes_carousel");
});

test("Quote carousel minimal layout and it's related options test", async () => {
    await testQuoteCarousel("s_quotes_carousel_minimal");
});

// TODO: Add the following test cases after task-5269350 by SHSA is merged.
// 1. Load the "website.carousel_slider" interaction.
// 2. Click on a slide and expect ".carousel-slide.o-focused-slide".
// 3. Click the next arrow and expect ".carousel-slide.o-focused-slide.active".
