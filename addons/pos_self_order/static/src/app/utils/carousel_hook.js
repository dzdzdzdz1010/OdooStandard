/* global Carousel */

import { onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { session } from "@web/session";

/**
 * Hook to automatically cycle through carousel media (images and videos).
 * - Images move to the next slide after a fixed interval (`timeIntervalSec`).
 * - Videos play from the beginning and switch to the next slide
 *   after their full duration.
 *
 * @param {string} refName
 *   Name of the OWL ref pointing to the carousel container element.
 * @param {number} [timeIntervalSec=5]
 *   Default interval (in seconds) used for image slides.
 */
export function useCarousel(refName, timeIntervalSec = 5) {
    const carouselRef = useRef(refName);
    let carousel = null;
    let carouselTimeout = null;

    const _clearTimeout = () => {
        if (carouselTimeout) {
            clearTimeout(carouselTimeout);
            carouselTimeout = null;
        }
    };

    const _getIntervalTime = () => {
        if (!carousel) {
            return 0;
        }
        const activeElement = carousel._activeElement || carousel._getItems()[0];
        const video = activeElement?.querySelector("video");
        if (!video) {
            return timeIntervalSec * 1000;
        }
        video.currentTime = 0;
        return (video.duration || timeIntervalSec) * 1000;
    };

    const _startTimeout = () => {
        _clearTimeout();
        carouselTimeout = setTimeout(
            () => carousel.next(),
            session.test_mode ? 100 : _getIntervalTime()
        );
    };

    onMounted(() => {
        carousel = new Carousel(carouselRef.el);
        carouselRef.el.addEventListener("slid.bs.carousel", _startTimeout);
        setTimeout(_startTimeout, 100);
    });

    onWillUnmount(() => {
        _clearTimeout();
        if (carouselRef.el) {
            carouselRef.el.removeEventListener("slid.bs.carousel", _startTimeout);
        }
    });
}
