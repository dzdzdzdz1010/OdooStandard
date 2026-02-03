export const useScrollToSelected = (containerRef, callback) => {
    const scrollToSelected = (itemEl) => {
        const containerEl = containerRef.el;
        const itemRect = itemEl.getBoundingClientRect();
        const containerRect = containerEl.getBoundingClientRect();
        const leftOverflow = itemRect.left - containerRect.left;
        const rightOverflow = itemRect.right - containerRect.right;
        const padding = 8;

        if (leftOverflow < 0) {
            containerEl.scrollBy({
                left: leftOverflow - padding,
                behavior: "smooth",
            });
        } else if (rightOverflow > 0) {
            containerEl.scrollBy({
                left: rightOverflow + padding,
                behavior: "smooth",
            });
        }
    };

    return (event, catId) => {
        callback(catId);
        scrollToSelected(event.currentTarget);
    };
};
