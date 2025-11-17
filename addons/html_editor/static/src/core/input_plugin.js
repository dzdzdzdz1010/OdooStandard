import { Plugin } from "../plugin";

/**
 * @typedef {((ev: InputEvent) => void)[]} beforeinput_listeners
 * @typedef {((ev: InputEvent) => void)[]} input_listeners
 */

export class InputPlugin extends Plugin {
    static id = "input";
    static dependencies = ["history"];
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.dependencies.history.stageSelection();
        this.trigger("beforeinput_listeners", ev);
    }

    onInput(ev) {
        this.dependencies.history.addStep();
        this.trigger("input_listeners", ev);
    }
}
