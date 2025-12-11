import { Countdown } from "./countdown";
import { registry } from "@web/core/registry";

const CountdownEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...super.dynamicContent,
            ".countdown_metrics": {
                // focus is needed here so we can listen to keydown events
                "t-on-click": (ev) => {
                    ev.currentTarget.focus();
                },
                "t-on-keydown": (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                },
            },
        };
        setup() {
            this.websiteEditService = this.services.website_edit;
            super.setup();
            this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
        }
        destroy() {
            super.destroy();
            this.enableIsCurrentStepModifiedWarning?.();
        }
        render() {
            const selectedNodes = this.websiteEditService.callShared(
                "selection",
                "getTargetedNodes"
            );
            // we shouldn't have the warning when we select the countdown
            // element, as it is being modified by the interaction
            this.enableIsCurrentStepModifiedWarning = this.websiteEditService.callShared(
                "history",
                "disableIsCurrentStepModifiedWarning"
            );
            if (selectedNodes?.some((node) => this.el.contains(node))) {
                // do not ignore the mutations if the countdown element is
                // selected as then history might become inconsistent if we
                // modify some countdown elements
                super.render();
            } else {
                this.websiteEditService.callShared(
                    "history",
                    "ignoreDOMMutations",
                    super.render.bind(this)
                );
                this.enableIsCurrentStepModifiedWarning?.();
            }
        }
        get shouldHideCountdown() {
            return false;
        }
        handleEndCountdownAction() {}
    };

registry.category("public.interactions.edit").add("website.countdown", {
    Interaction: Countdown,
    mixin: CountdownEdit,
});
