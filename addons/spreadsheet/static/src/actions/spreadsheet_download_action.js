<<<<<<< 7c8de60b9eb243dcbd41bb439c6a98240f4ecade
||||||| c4b1ca0d3948f830b78193df9a4d95c2b68b8a72
/** @odoo-module */

=======
/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
>>>>>>> 9df2f8890384481775a258a1d7c7f09ec613506e
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { createSpreadsheetModel, waitForDataLoaded } from "@spreadsheet/helpers/model";
import { user } from "@web/core/user";

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {object} action
 */
async function downloadSpreadsheet(env, action) {
    const canExport = await user.hasGroup("base.group_allow_export");
    if (!canExport) {
        env.services.notification.add(
            _t("You don't have the rights to export data. Please contact an Administrator."),
            {
                title: _t("Access Error"),
                type: "danger",
            }
        );
        return;
    }
    let { name, data, sources, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const model = await createSpreadsheetModel({ env, data, revisions: stateUpdateMessages });
        await waitForDataLoaded(model);
        sources = model.getters.getLoadedDataSources();
        xlsxData = model.exportXLSX();
    }
    await download({
        url: "/spreadsheet/xlsx",
        data: {
            zip_name: `${name}.xlsx`,
            files: new Blob([JSON.stringify(xlsxData.files)], {
                type: "application/json",
            }),
            datasources: new Blob([JSON.stringify(sources)], {
                type: "application/json",
            }),
        },
    });
}

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
