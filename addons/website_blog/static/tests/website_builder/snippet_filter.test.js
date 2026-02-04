import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("dynamic Snippet Blog Filter", async () => {
    // We just need to fulfill these two RPCs, they are not useful in test.
    onRpc(
        "/website/snippet/options_filters",
        async (args) =>
            new Promise((resolve) => {
                resolve([]);
            })
    );
    onRpc(
        "/website/snippet/filter_templates",
        async (args) =>
            new Promise((resolve) => {
                resolve([]);
            })
    );

    // Provide blogs, tags and authors for the filters
    onRpc("blog.blog", "search_read", () => [
        {
            id: 1,
            name: "Test Blog 1",
        },
    ]);
    onRpc("blog.tag", "search_read", () => [{ id: 1, name: "Adventure" }]);
    onRpc("blog.post", "formatted_read_group", () => [
        {
            author_id: [1, "Author 1"],
            __count: 1,
        },
    ]);

    await setupWebsiteBuilderWithSnippet(["s_blog_posts"]);
    await contains(":iframe .s_blog_posts").click();

    // Check for blog filter
    await contains("[data-label=Blog] button.dropdown").click();
    await contains(".dropdown-item:contains(All Blogs)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-blog-id", "-1");
    await contains("[data-label=Blog] button.dropdown").click();
    await contains(".dropdown-item:contains(Test Blog 1)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-blog-id", "1");

    // Check for tag filter
    await contains("[data-label=Tag] button.dropdown").click();
    await contains(".dropdown-item:contains(All Tags)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-tag-id", "-1");
    await contains("[data-label=Tag] button.dropdown").click();
    await contains(".dropdown-item:contains(Adventure)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-tag-id", "1");

    // Check for author filter
    await contains("[data-label=Author] button.dropdown").click();
    await contains(".dropdown-item:contains(All Authors)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-author-id", "-1");
    await contains("[data-label=Author] button.dropdown").click();
    await contains(".dropdown-item:contains(Author 1)").click();
    expect(":iframe .s_blog_posts").toHaveAttribute("data-filter-by-author-id", "1");
});
