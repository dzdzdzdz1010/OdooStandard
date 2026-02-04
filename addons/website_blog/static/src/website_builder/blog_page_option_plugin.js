import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class BlogPageOption extends BaseOptionComponent {
    static template = "website_blog.BlogPageOption";
    static selector = "main:has(#o_wblog_post_main)";
    static title = _t("Blog Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class BlogPageOptionPlugin extends Plugin {
    static id = "blogPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [BlogPageOption],
        content_not_editable_selectors: [".o_list_cover"],
        builder_actions: {
            ToggleRecommendedBlogAction,
        },
    };
}

export class ToggleRecommendedBlogAction extends BuilderAction {
    static id = "toggleRecommendedBlog";
    static dependencies = ["savePlugin"];

    getFooterDivEl(editingElement) {
        return editingElement.querySelector("#o_wblog_post_footer div");
    }

    getValue({ editingElement }) {
        const footerDivEl = this.getFooterDivEl(editingElement);
        return JSON.stringify({ id: parseInt(footerDivEl?.dataset?.recommendedBlogPostId || 0) });
    }

    isApplied({ editingElement }) {
        const footerDivEl = this.getFooterDivEl(editingElement);
        return parseInt(footerDivEl?.dataset?.recommendedBlogPostId) > 0;
    }

    async apply({ editingElement, value, isPreviewing }) {
        if (!isPreviewing) {
            const blogPostId = parseInt(editingElement.querySelector("#wrap").dataset?.blogPostId);
            if (!blogPostId) {
                return;
            }
            const recommendedId = JSON.parse(value).id;
            await this.services.orm.write("blog.post", [blogPostId], {
                recommended_post_id: recommendedId,
            });

            // Persist changes explicitly as reloadEditor resets unsaved plugin
            // state.
            await this.dependencies.savePlugin.save();

            // Reload editor to reflect updated next post configuration.
            this.config.reloadEditor();
        }
    }
}

registry.category("website-plugins").add(BlogPageOptionPlugin.id, BlogPageOptionPlugin);
