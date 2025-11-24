import { BannerPlugin } from "@html_editor/main/banner_plugin";

export class CommandLessBannerPlugin extends BannerPlugin {
    resources = {
        ...super.resources,
        user_commands: [],
    };
}
