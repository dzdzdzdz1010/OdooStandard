import { BlockTab } from "@html_builder/sidebar/block_tab";
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(BlockTab.prototype, {
    setup() {
        super.setup();
        this.websiteService = useService("website");

        onMounted(() => {
            if (this.websiteService.context?.newInstalledModule) {
                const { snippetTitle } = JSON.parse(
                    decodeURIComponent(this.websiteService.context.newInstalledModule)
                );
                if (snippetTitle) {
                    this.handlePostModuleInstall(snippetTitle);
                }
            }
        });
    },

    /**
     * Opens the corresponding snippet group dialog after the installation of a
     * newly installed snippet module.
     *
     * @param {string} snippetTitle - The title of the snippet group to open.
     */
    async handlePostModuleInstall(snippetTitle) {
        delete this.websiteService.context.newInstalledModule;
        const snippet = this.snippetModel.snippetGroups.find(
            (snippetEl) => snippetEl.title === snippetTitle
        );
        if (snippet) {
            await this.onSnippetGroupClick(snippet);
        }
    },
});
