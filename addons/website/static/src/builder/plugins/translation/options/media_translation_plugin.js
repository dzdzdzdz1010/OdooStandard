import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    TranslateDocumentOption,
    TranslateImageOption,
    TranslateVideoOption,
} from "@website/builder/plugins/translation/options/media_translation_option";

export class MediaTranslationPlugin extends Plugin {
    static id = "mediaTranslation";
    static dependencies = ["translation"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [TranslateImageOption, TranslateVideoOption, TranslateDocumentOption],
        builder_actions: {
            TranslateMediaSrcAction,
        },
        on_image_saved_handlers: ({ imageEl }) => {
            if (this.dependencies.translation.getTranslationInfo(imageEl)) {
                const translatedSrc = imageEl.getAttribute("src");
                this.dependencies.translation.updateTranslationMap(
                    imageEl,
                    translatedSrc,
                    "data-oe-translatable-link"
                );
            }
        },
    };
}

registry.category("translation-plugins").add(MediaTranslationPlugin.id, MediaTranslationPlugin);

export class TranslateMediaSrcAction extends BuilderAction {
    static id = "translateMediaSrc";
    static dependencies = ["history", "imagePostProcess", "media", "translation"];

    setup() {
        this.savingMap = {
            images: this.saveImage.bind(this),
            videos: this.saveVideo.bind(this),
            documents: this.saveDocument.bind(this),
        };
    }

    async apply({ editingElement, params: { mainParam: mediaType } }) {
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: mediaType === "images",
                noImages: mediaType !== "images",
                visibleTabs: [mediaType.toUpperCase()],

                node: editingElement,
                save: async (newMediaEl) => {
                    await this.savingMap[mediaType](editingElement, newMediaEl);
                },
            });
            onClose.then(resolve);
        });
    }

    async saveImage(editingElement, newImgEl) {
        // TODO @image-translate: this is a one-to-one "translation" of the
        // image. We bring back from the original image all the manipulations
        // that have been done: shape, resizing, filters... But if the image is
        // different, those options should also be adaptable. We should have
        // translation options to handle the new image exactly like what is
        // possible in the builder.
        const attributesToKeep = ["oeTranslationState", "oeTranslatableLink"];
        const newDataset = { ...editingElement.dataset, ...newImgEl.dataset };
        for (const dataAttribute in newDataset) {
            if (!attributesToKeep.includes(dataAttribute)) {
                if (dataAttribute in newImgEl.dataset) {
                    editingElement.dataset[dataAttribute] = newImgEl.dataset[dataAttribute];
                } else {
                    delete editingElement.dataset[dataAttribute];
                }
            }
        }
        editingElement.setAttribute("src", newImgEl.getAttribute("src"));
        const updateImageAttributes = await this.dependencies.imagePostProcess.processImage({
            img: editingElement,
        });
        updateImageAttributes();
        editingElement.classList.add("oe_translated");
    }

    saveVideo(editingElement, newVideoEl) {
        const originalLink =
            this.dependencies.translation.getTranslationInfo(editingElement)["data-oe-expression"]
                .translation;
        const newSrc = newVideoEl.querySelector("iframe").getAttribute("src");
        editingElement.setAttribute("data-oe-expression", newSrc);
        editingElement.querySelector("iframe").setAttribute("src", newSrc);
        editingElement.classList.add("oe_translated");

        const updateTranslationMap = this.dependencies.translation.updateTranslationMap;
        this.dependencies.history.applyCustomMutation({
            apply: () => {
                updateTranslationMap(editingElement, newSrc, "data-oe-expression");
            },
            revert: () => {
                updateTranslationMap(editingElement, originalLink, "data-oe-expression");
            },
        });
    }

    saveDocument(editingElement, newFileEl) {
        editingElement.replaceChildren(...newFileEl.children);
        editingElement.dataset.attachmentId = newFileEl.dataset.attachmentId;
        editingElement.querySelector("a.o_link_readonly").classList.add("o_translate_inline");
    }
}
