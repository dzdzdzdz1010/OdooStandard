import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    many2ManyBinaryField,
    Many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

export class MailComposerAttachmentList extends Many2ManyBinaryField {
    static template = "mail.MailComposerAttachmentList";
    /** @override */
    setup() {
        super.setup();
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
    }
    /**
     * @override
     * @param {integer} fileId
     */
    async onFileRemove(fileId) {
        super.onFileRemove(fileId);
<<<<<<< dfcd5e63547c75b8eec60f6937e25e67cbf31455
        const attachment = this.mailStore["ir.attachment"].insert(fileId);
        await this.attachmentUploadService.unlink(attachment);
||||||| f95bcc097fd7e70af8d28a66c010ae9b9490f439
        const attachment = this.mailStore.Attachment.insert(fileId);
        if (attachment) {
            await this.attachmentUploadService.unlink(attachment);
        }
=======
        const attachment = this.mailStore.Attachment.insert(fileId);
        if (attachment && attachment.res_model === "mail.compose.message") {
            await this.attachmentUploadService.unlink(attachment);
        }
>>>>>>> ab0dba58afd69bf5e4ed622d4f9cdecca0ac0790
        this.env.fullComposerBus.trigger("ATTACHMENT_REMOVED", {
            id: attachment.id,
        });
    }
}

export const mailComposerAttachmentList = {
    ...many2ManyBinaryField,
    component: MailComposerAttachmentList,
};

registry.category("fields").add("mail_composer_attachment_list", mailComposerAttachmentList);
