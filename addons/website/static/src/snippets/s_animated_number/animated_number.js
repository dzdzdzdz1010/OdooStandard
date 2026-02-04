import { BaseAnimation } from "@website/interactions/base_animation";
import { registry } from "@web/core/registry";

export class AnimatedNumber extends BaseAnimation {
    static selector = ".s_animated_number";
    dynamicContent = {
        ...this.dynamicContent,
        _document: {
            // Setting capture to true allows to take advantage of event
            // bubbling for events that otherwise don’t support it. (e.g. useful
            // when scrolling a modal)
            "t-on-scroll.capture": this.throttled(this.scrollWebsiteAnimate),
        },
    };

    setup() {
        super.setup();

        const dataset = this.el.dataset;
        this.startValue = parseInt(dataset.startValue);
        this.endValue = parseInt(dataset.endValue);
        this.duration = parseInt(dataset.duration);
        this.prefix = dataset.prefix;
        this.postfix = dataset.postfix;

        this.scrollingElement = this.el.ownerDocument.scrollingElement;
        this.animationState = "";
    }

    start() {
        if (this.el.closest(".dropdown")) {
            return;
        }
        this.scrollWebsiteAnimate();
    }

    scrollWebsiteAnimate() {
        if (this.animationState) {
            return;
        }
        const { visible } = super.scrollWebsiteAnimate();
        if (visible) {
            this.startAnimation();
        }
    }

    startAnimation() {
        this.animationState = "inProgress";
        let targetEl = this.el.querySelector(".s_animated_number_display");
        while (targetEl.childNodes.length == 1) {
            targetEl = targetEl.firstChild;
        }
        const startValue = this.startValue;
        const endValue = this.endValue;
        const duration = this.duration;
        const prefix = this.prefix || "";
        const postfix = this.postfix || "";

        const startTime = performance.now();

        function animate() {
            const elapsed = performance.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // General Alternatives :
            // easeOutSine: x -> Math.sin((x * Math.PI) / 2)
            // easeOutCubic: x -> 1 - Math.pow(1 - x, 3)
            // easeOutQuint: x -> 1 - Math.pow(1 - x, 5)
            const easedProgress = 1 - Math.pow(1 - progress, 5);
            const value = startValue + (endValue - startValue) * easedProgress;

            targetEl.textContent = prefix + Math.round(value) + postfix;

            if (progress < 1) {
                this.waitForAnimationFrame(animate);
            } else {
                this.animationCompleted = "done";
            }
        }

        this.waitForAnimationFrame(animate);
    }
}

registry.category("public.interactions").add("website.animated_number", AnimatedNumber);

registry.category("public.interactions.edit").add("website.animated_number", {
    Interaction: AnimatedNumber,
});
