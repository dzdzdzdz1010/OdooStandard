import { fields, Record } from "@mail/model/export";

export class ScheduledMessage extends Record {
    static _name = "mail.scheduled.message";
    static id = "id";
    /** @type {Object.<number, import("models").ScheduledMessage>} */
    static records = {};
    /** @returns {import("models").ScheduledMessage} */
    static get(data) {
        return super.get(data);
    }
    /** @type {number} */
    id;
    attachment_ids = fields.Many("ir.attachment");
    author_id = fields.One("res.partner");
    body = fields.Html("");
    /** @type {boolean} */
    composition_batch;
    /** @type {boolean} */
    is_note;
    scheduled_date = fields.Datetime();
    thread = fields.One("mail.thread");
}

ScheduledMessage.register();
