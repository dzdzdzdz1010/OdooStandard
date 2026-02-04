import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DynamicSnippetBlogPostsOption } from "./dynamic_snippet_blog_posts_option";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['fetchBlogs'] } fetchBlogs
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchBlogs", "fetchTags", "fetchAuthors", "getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, DynamicSnippetBlogPostsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    setup() {
        this.data = Object.create(null);
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(DynamicSnippetBlogPostsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", -1);
            setDatasetIfUndefined(snippetEl, "filterByTagId", -1);
            setDatasetIfUndefined(snippetEl, "filterByAuthorId", -1);
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchBlogs() {
        return (this.data.blogs ??= this._fetchData("blog.blog", true));
    }

    async fetchTags() {
        return (this.data.tags ??= this._fetchData("blog.tag"));
    }

    async fetchAuthors() {
        if (!this.data.authors) {
            const websiteDomain = this._websiteDomain();
            this.data.authors = await this.services.orm
                .formattedReadGroup("blog.post", websiteDomain, ["author_id"], [])
                .then((results) =>
                    results.map((r) => ({ id: r.author_id[0], name: r.author_id[1] }))
                );
        }
        return this.data.authors;
    }

    async _fetchData(model, applyDomain = false) {
        // TODO put in an utility function
        let websiteDomain = [];
        if (applyDomain) {
            websiteDomain = this._websiteDomain();
        }
        return this.services.orm.searchRead(model, websiteDomain, ["id", "name"]);
    }

    _websiteDomain() {
        const websiteId = this.services.website.currentWebsite.id;
        return ["|", ["website_id", "=", false], ["website_id", "=", websiteId]];
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
