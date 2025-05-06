/**
 * This file is meant to load the different subparts of the module
 * to guarantee their plugins are loaded in the right order
 *
 * dependency:
 *             other plugins
 *                   |
 *                  ...
 *                   |
 *                filters
 *                /\    \
 *               /  \    \
 *           pivot  list  Odoo chart
 */

/** TODO: Introduce a position parameter to the plugin registry in order to load them in a specific order */
import * as spreadsheet from "@odoo/o-spreadsheet";
const { corePluginRegistry, coreViewsPluginRegistry, featurePluginRegistry } = spreadsheet.registries;

import {
  GlobalFiltersCorePlugin,
  GlobalFiltersUIPlugin,
  GlobalFiltersCoreViewPlugin,
} from "@spreadsheet/global_filters/index";
import { PivotOdooCorePlugin, PivotCoreViewGlobalFilterPlugin, PivotUIGlobalFilterPlugin } from "@spreadsheet/pivot/index"; // list depends on filter for its getters
import { ListCorePlugin, ListCoreViewPlugin, ListUIPlugin } from "@spreadsheet/list/index"; // pivot depends on filter for its getters
import {
    ChartOdooMenuPlugin,
    OdooChartCorePlugin,
    OdooChartUIPlugin,
} from "@spreadsheet/chart/index"; // Odoochart depends on filter for its getters
import { PivotCoreGlobalFilterPlugin } from "./pivot/plugins/pivot_core_global_filter_plugin";
import { PivotOdooUIPlugin } from "./pivot/plugins/pivot_odoo_ui_plugin";
import { LoggingUIPlugin } from "@spreadsheet/logging/logging_ui_plugin";

corePluginRegistry.add("OdooGlobalFiltersCorePlugin", GlobalFiltersCorePlugin);
corePluginRegistry.add("PivotOdooCorePlugin", PivotOdooCorePlugin);
corePluginRegistry.add("OdooPivotGlobalFiltersCorePlugin", PivotCoreGlobalFilterPlugin);
corePluginRegistry.add("OdooListCorePlugin", ListCorePlugin);
corePluginRegistry.add("odooChartCorePlugin", OdooChartCorePlugin);
corePluginRegistry.add("chartOdooMenuPlugin", ChartOdooMenuPlugin);

coreViewsPluginRegistry.add("OdooGlobalFiltersCoreViewPlugin", GlobalFiltersCoreViewPlugin);
coreViewsPluginRegistry.add("OdooPivotGlobalFiltersCoreViewPlugin", PivotCoreViewGlobalFilterPlugin);
coreViewsPluginRegistry.add("OdooListCoreViewPlugin", ListCoreViewPlugin);
coreViewsPluginRegistry.add("odooChartUIPlugin", OdooChartUIPlugin);
<<<<<<< 7c8de60b9eb243dcbd41bb439c6a98240f4ecade

featurePluginRegistry.add("OdooPivotGlobalFilterUIPlugin", PivotUIGlobalFilterPlugin);
featurePluginRegistry.add("OdooGlobalFiltersUIPlugin", GlobalFiltersUIPlugin);
featurePluginRegistry.add("odooPivotUIPlugin", PivotOdooUIPlugin);
featurePluginRegistry.add("odooListUIPlugin", ListUIPlugin);
||||||| c4b1ca0d3948f830b78193df9a4d95c2b68b8a72
coreViewsPluginRegistry.add("odooPivotUIPlugin", PivotOdooUIPlugin);
=======
coreViewsPluginRegistry.add("odooPivotUIPlugin", PivotOdooUIPlugin);
coreViewsPluginRegistry.add("OdooLoggingUIPlugin", LoggingUIPlugin);
>>>>>>> 9df2f8890384481775a258a1d7c7f09ec613506e
