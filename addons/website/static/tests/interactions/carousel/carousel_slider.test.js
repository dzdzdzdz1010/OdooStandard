import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.carousel_slider");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("carousel_slider updates min height of carousel items", async () => {
    // Use a dummy base64 image for all images, so that the test doesn't need to
    // fetch any image and risk stalling on load.
    const base64Image =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAH0lEQVQYV2NkQAL/GRikGGF8KOcZWADGAbEZkTkgAQDXKwcebKRDwQAAAABJRU5ErkJggg==";
    const { core } = await startInteractions(`
        <section>
            <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="false" data-bs-interval="0">
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="${base64Image}" data-name="Image" data-index="0" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="${base64Image}" data-name="Image" data-index="1" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="${base64Image}" data-name="Image" data-index="2" alt=""/>
                    </div>
                </div>
                <div class="o_carousel_controllers">
                    <button class="carousel-control-prev o_not_editable" contenteditable="false" t-attf-data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                        <span class="carousel-control-prev-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <div class="carousel-indicators">
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" class="active">
                            <span class="visually-hidden">Carousel indicator</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="${base64Image}"/>
                        </button>
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="1">
                            <span class="visually-hidden">Carousel indicator</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="${base64Image}"/>
                        </button>
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="2">
                            <span class="visually-hidden">Carousel indicator</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="${base64Image}"/>
                        </button>
                    </div>
                    <button class="carousel-control-next o_not_editable" contenteditable="false" t-attf-data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                        <span class="carousel-control-next-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Next</span>
                    </button>
                </div>
            </div>
        </section>
    `);
    const itemEls = queryAll(".carousel-item");
    const minHeight = itemEls[0].style.minHeight;

    expect(core.interactions).toHaveLength(1);
    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ "min-height": minHeight }, { inline: true });
    }

    core.stopInteractions();

    expect(core.interactions).toHaveLength(0);
    for (const itemEl of itemEls) {
        expect(itemEl).not.toHaveStyle({ minHeight });
    }
});
