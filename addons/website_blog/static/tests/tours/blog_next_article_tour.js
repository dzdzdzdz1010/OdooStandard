import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "check_blog_next_article_with_admin",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Open the blog 'Post Test 1'",
            trigger: ":iframe .o_wblog_post a:contains('Post Test 1')",
            run: "click",
        },
        {
            content: "Check if the next article is 'Post Test 2'",
            trigger: ":iframe .o_wblog_post_title .o_wblog_post_name:contains('Post Test 2')",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on the style tab.",
            trigger: "button[data-name='customize']",
            run: "click",
        },
        ...changeOptionInPopover("Blog Page", "Recommended Post", "Post Test 4"),
        {
            content: "Check if the recommended article is 'Post Test 4'",
            trigger: ":iframe .o_wblog_post_title .o_wblog_post_name:contains('Post Test 4')",
        },
    ]
);

registry.category("web_tour.tours").add("check_blog_next_article_with_user", {
    url: "/blog",
    steps: () => [
        {
            content: "Open the blog 'Post Test 4'",
            trigger: ".o_wblog_post a:contains('Post Test 4')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Check if the next article is 'Post Test 1'",
            trigger: ".o_wblog_post_title .o_wblog_post_name:contains('Post Test 1')",
        },
    ],
});
