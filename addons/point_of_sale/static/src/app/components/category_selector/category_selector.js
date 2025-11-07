import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class CategorySelector extends Component {
    static template = "point_of_sale.CategorySelector";
    static props = {};

    setup() {
        this.ui = useService("ui");
        this.pos = usePos();
    }

    getCategoriesList(list, allParents, depth) {
        const categoriesList = [...list];
        list.forEach((item) => {
            if (item.id === allParents[depth]?.id) {
                const children = this.getChildren(item);
                if (children.length) {
                    categoriesList.push(...this.getCategoriesList(children, allParents, depth + 1));
                }
            }
        });
        return categoriesList;
    }

    getCategoriesAndSub() {
        const displayableCategories = this.getDisplayableCategories();
        const displayableCategoriesSet = new Set(displayableCategories);
        this.displayableCategoriesSet = displayableCategoriesSet;
        const rootCategories = displayableCategories
            .filter(
                (category) =>
                    !category.parent_id || !displayableCategoriesSet.has(category.parent_id)
            )
            .sort((a, b) => a.sequence - b.sequence);
        const selected = this.pos.selectedCategory ? [this.pos.selectedCategory] : [];
        const allParents = selected
            .concat(this.getAllParents(this.pos.selectedCategory, displayableCategoriesSet))
            .reverse();
        const result = this.getCategoriesList(rootCategories, allParents, 0)
            .flat(Infinity)
            .filter((c) => c.hasProductsToShow)
            .map((c) => this.getChildCategoriesInfo(c, rootCategories));
        this.displayableCategoriesSet = null;
        return result;
    }

    getAncestorsAndCurrent() {
        const selectedCategory = this.pos.selectedCategory;
        const displayableCategoriesSet = this.displayableCategoriesSet;
        return selectedCategory
            ? [
                  undefined,
                  ...this.getAllParents(selectedCategory, displayableCategoriesSet),
                  selectedCategory,
              ]
            : [selectedCategory];
    }

    getChildCategoriesInfo(category, rootCategories) {
        return {
            ...pick(category, "id", "name", "color"),
            imgSrc:
                this.pos.config.show_category_images && category.has_image
                    ? `/web/image?model=pos.category&field=image_128&id=${category.id}`
                    : undefined,
            isSelected: this.getAncestorsAndCurrent().includes(category),
            isChildren: this.getChildCategories(this.pos.selectedCategory, rootCategories).includes(
                category
            ),
        };
    }

    getChildCategories(selectedCategory, rootCategories) {
        return selectedCategory ? this.getChildren(selectedCategory) : rootCategories;
    }

    getDisplayableCategories() {
        const { limit_categories, iface_available_categ_ids } = this.pos.config;
        if (limit_categories && iface_available_categ_ids.length > 0) {
            return iface_available_categ_ids;
        }
        return this.pos.models["pos.category"].getAll();
    }

    getChildren(category) {
        const displayableCategoriesSet = this.displayableCategoriesSet;
        return (
            category.child_ids
                ?.filter((child) => displayableCategoriesSet.has(child))
                .sort((a, b) => a.sequence - b.sequence) || []
        );
    }

    getAllParents(category, displayableCategoriesSet) {
        return category?.allParents.filter((cat) => displayableCategoriesSet.has(cat)) || [];
    }
}
