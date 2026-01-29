import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { EventRegistrationPopup } from "../../components/popup/event_registration_popup/event_registration_popup";
import { EventSlotSelectionPopup } from "../../components/popup/event_slot_selection_popup/event_slot_selection_popup";

const { DateTime } = luxon;

patch(ProductScreen.prototype, {
    get products() {
        const products = super.products;
        return [...products].filter((p) => p.service_tracking !== "event");
    },
    getProductImage(product) {
        if (!product.event_id) {
            return super.getProductImage(product);
        }

        return `/web/image?model=event.event&id=${product.event_id.id}&field=image_1024&unique=${product.event_id.write_date}`;
    },
    async addProductToOrder(product) {
        if (!product.event_id) {
            return await super.addProductToOrder(product);
        }

        if (product.event_id.seats_available === 0 && product.event_id.seats_limited) {
            this.notification.add("No more seats available for this event", {
                type: "danger",
            });
            return;
        }

        const event = product.event_id;
        const tickets = event.event_ticket_ids.filter(
            (ticket) => ticket.product_id && ticket.product_id.service_tracking === "event"
        );

        // Used to dynamically update the event ticket availabilities depending on
        // the current order already validated event registrations.
        const currentOrderEventRegistrations = (this.pos.getOrder()?.lines || []).reduce(
            (acc, line) => {
                const regs = (line.event_registration_ids.flat() || []).filter(
                    (reg) => reg.event_id?.id === event.id
                );
                return acc.concat(regs);
            },
            []
        );

        const currentOrderRegCounts = currentOrderEventRegistrations.reduce(
            (acc, reg) => {
                const slotId = reg.event_slot_id?.id;
                const ticketId = reg.event_ticket_id?.id;
                // Per slot & ticket
                if (slotId && ticketId) {
                    if (!acc.perSlotTicket[ticketId]) {
                        acc.perSlotTicket[ticketId] = {};
                    }
                    acc.perSlotTicket[ticketId][slotId] =
                        (acc.perSlotTicket[ticketId][slotId] || 0) + 1;
                }
                // Per slot
                if (slotId) {
                    acc.perSlot[slotId] = (acc.perSlot[slotId] || 0) + 1;
                }
                // Per ticket
                if (ticketId) {
                    acc.perTicket[ticketId] = (acc.perTicket[ticketId] || 0) + 1;
                }
                return acc;
            },
            { perSlotTicket: {}, perSlot: {}, perTicket: {} }
        );

        // Multi Slot
        let avaibilityByTicket = {};
        let slotResult = {};
        let slotSelected;
        let slotTicketAvailabilities = {};
        if (event.is_multi_slots) {
            // Updating data in case of event change
            await this.pos.data.read(
                "event.event",
                [event.id],
                ["event_slot_ids", "seats_available", "seats_limited"]
            );
            await this.pos.data.read(
                "event.slot",
                event.event_slot_ids.map((slot) => slot.id)
            );
            const slotTickets = [];
            const slots = event.event_slot_ids.filter(
                (slot) => slot.start_datetime > DateTime.now()
            );
            for (const ticket of tickets) {
                for (const slot of slots) {
                    slotTickets.push([slot.id, ticket.id]);
                }
            }
            slotTicketAvailabilities = await this.pos.data.call(
                "event.event",
                "get_slot_tickets_availability_pos",
                [event.id, slotTickets]
            );
            const eventSeats = event.seats_limited
                ? Math.max(0, event.seats_available - currentOrderEventRegistrations.length)
                : "unlimited";
            avaibilityByTicket = slotTicketAvailabilities.reduce((acc, availability, idx) => {
                const ticketsData = slotTickets[idx];
                const slotId = ticketsData[0];
                const ticketId = ticketsData[1];
                const currentTicketCount = currentOrderRegCounts.perTicket[ticketId] ?? 0;
                const currentSlotTicketCount =
                    currentOrderRegCounts.perSlotTicket[ticketId]?.[slotId] ?? 0;
                const limitMaxPerOrder =
                    tickets.find((t) => t.id === ticketId)?.limit_max_per_order ?? 0;
                if (!acc[ticketId]) {
                    acc[ticketId] = {};
                }
                if (!acc[ticketId][slotId]) {
                    acc[ticketId][slotId] = {};
                }
                const remainingSlotTicketAvailability = availability - currentSlotTicketCount;
                if (limitMaxPerOrder > 0) {
                    // The limit max per order is per ticket (not per slot ticket),
                    // it needs to consider the current order ticket count.
                    const remainingOrderTicketAvailability = limitMaxPerOrder - currentTicketCount;
                    if (availability === null) {
                        availability = remainingOrderTicketAvailability;
                    } else {
                        availability = Math.min(
                            remainingOrderTicketAvailability,
                            remainingSlotTicketAvailability
                        );
                    }
                    acc[ticketId][slotId] = Math.max(0, availability);
                } else if (availability === null) {
                    acc[ticketId][slotId] = "unlimited";
                } else if (typeof availability === "number") {
                    acc[ticketId][slotId] = Math.max(0, remainingSlotTicketAvailability);
                } else {
                    acc[ticketId][slotId] = 0;
                }
                return acc;
            }, {});
            const isAvailable = Object.values(avaibilityByTicket).some((av) =>
                Object.values(av).some((a) => (typeof a === "number" && a > 0) || a === "unlimited")
            );
            if (!isAvailable || eventSeats === 0) {
                this.notification.add("All slots are booked out for this event.", {
                    type: "danger",
                });
                return;
            }
            // NB: The slot availability cannot be the sum of every slot-ticket availabilities
            // because each slot-ticket availability is only accurate if the user tries to register to this slot-ticket only.
            // However here the UI allows different tickets selection, so making the sum of every slot-ticket availabilities
            // will potentially exceed the event/slot limitations.
            const availabilityPerSlot = slots.reduce((acc, slot) => {
                const slotId = slot.id;
                const isEventLimited = event.seats_limited && event.seats_max > 0;
                const currentOrderSlotRegCount = currentOrderRegCounts.perSlot[slot.id] ?? 0;
                const totalTicketAvailability = !tickets.some((ticket) => ticket.seats_max === 0)
                    ? tickets.reduce((sum, ticket) => sum + (ticket.seats_available || 0), 0)
                    : "unlimited";

                let availability = 0;
                if (isEventLimited && totalTicketAvailability === "unlimited") {
                    // Event = limited seats, Tickets = total is unlimited
                    availability = slot.seats_available;
                } else if (isEventLimited && totalTicketAvailability !== "unlimited") {
                    // Event = limited seats, Tickets = total is limited
                    availability = Math.min(slot.seats_available, totalTicketAvailability);
                } else if (!event.seats_limited) {
                    // Event = unlimited seats
                    availability = totalTicketAvailability;
                }
                if (availability !== "unlimited") {
                    availability = Math.max(0, availability - currentOrderSlotRegCount);
                }
                acc[slotId] = availability;
                return acc;
            }, {});
            slotResult = await makeAwaitable(this.dialog, EventSlotSelectionPopup, {
                availabilityPerSlot: availabilityPerSlot,
                event: event,
            });
            if (!slotResult?.slotId) {
                return;
            }
            slotSelected = this.pos.models["event.slot"].get(slotResult.slotId);
        } else {
            avaibilityByTicket = tickets.reduce((acc, ticket) => {
                const currentTicketCount = currentOrderRegCounts.perTicket[ticket.id] ?? 0;
                const limitMaxPerOrder = ticket.limit_max_per_order ?? 0;
                let availability;
                if (ticket.seats_max === 0 && !event.seats_limited) {
                    // Event = unlimited seats, Ticket = unlimited seats
                    availability = "unlimited";
                } else if (ticket.seats_max === 0) {
                    // Event = limited seats, Ticket = unlimited seats
                    availability = event.seats_available;
                } else {
                    // Event = unlimited seats, Ticket = limited seats
                    availability = ticket.seats_available;
                }
                if (limitMaxPerOrder > 0) {
                    availability =
                        availability === "unlimited"
                            ? limitMaxPerOrder
                            : Math.min(limitMaxPerOrder, availability);
                }
                if (availability !== "unlimited") {
                    availability = Math.max(0, availability - currentTicketCount);
                }
                acc[ticket.id] = availability;
                return acc;
            }, {});
        }

        const ticketResult = await makeAwaitable(this.dialog, EventConfiguratorPopup, {
            availabilityPerTicket: avaibilityByTicket,
            slotResult: slotResult,
            tickets: tickets,
        });
        if (!ticketResult || !ticketResult.length) {
            return;
        }

        const result = await makeAwaitable(this.dialog, EventRegistrationPopup, {
            event: event,
            data: ticketResult,
        });

        if (!result || !result.byRegistration || !Object.keys(result.byRegistration).length) {
            return;
        }

        const { globalSimpleChoice, globalTextAnswer } = Object.entries(result.byOrder).reduce(
            (acc, [questionId, answer]) => {
                const question = this.pos.models["event.question"].get(parseInt(questionId));
                if (
                    question.question_type === "simple_choice" &&
                    this.pos.models["event.question.answer"].get(parseInt(answer))
                ) {
                    acc.globalSimpleChoice[questionId] = answer;
                } else if (answer) {
                    acc.globalTextAnswer[questionId] = answer;
                }

                return acc;
            },
            { globalSimpleChoice: {}, globalTextAnswer: {} }
        );

        for (const [ticketId, data] of Object.entries(result.byRegistration)) {
            const ticket = this.pos.models["event.event.ticket"].get(parseInt(ticketId));
            const line = await this.pos.addLineToCurrentOrder({
                product_id: ticket.product_id,
                product_tmpl_id: ticket.product_id.product_tmpl_id,
                price_unit: ticket.price,
                price_type: "original",
                qty: data.length,
                event_ticket_id: ticket,
                event_slot_id: slotSelected,
            });

            for (const registration of data) {
                const userData = {};
                for (const [questionId, answer] of Object.entries(registration)) {
                    const question = this.pos.models["event.question"].get(parseInt(questionId));

                    if (!question) {
                        continue;
                    }

                    if (question.question_type === "email") {
                        userData.email = answer;
                    } else if (question.question_type === "phone") {
                        userData.phone = answer;
                    } else if (question.question_type === "name") {
                        userData.name = answer;
                    } else if (question.question_type === "company_name") {
                        userData.company_name = answer;
                    }
                }

                const { simpleChoice, textAnswer } = Object.entries(registration).reduce(
                    (acc, [questionId, answer]) => {
                        const question = this.pos.models["event.question"].get(
                            parseInt(questionId)
                        );
                        if (
                            question.question_type === "simple_choice" &&
                            this.pos.models["event.question.answer"].get(parseInt(answer))
                        ) {
                            acc.simpleChoice[questionId] = answer;
                        } else if (answer) {
                            acc.textAnswer[questionId] = answer;
                        }

                        return acc;
                    },
                    { simpleChoice: {}, textAnswer: {} }
                );
                // This will throw an error on creation if not possible (python constraint)
                this.pos.models["event.registration"].create({
                    ...userData,
                    event_id: event,
                    event_ticket_id: ticket,
                    event_slot_id: slotSelected,
                    pos_order_line_id: line,
                    partner_id: this.pos.getOrder().partner_id,
                    registration_answer_ids: Object.entries({
                        ...textAnswer,
                        ...globalTextAnswer,
                    }).map(([questionId, answer]) => [
                        "create",
                        {
                            question_id: this.pos.models["event.question"].get(
                                parseInt(questionId)
                            ),
                            value_text_box: answer,
                        },
                    ]),
                    registration_answer_choice_ids: Object.entries({
                        ...simpleChoice,
                        ...globalSimpleChoice,
                    }).map(([questionId, answer]) => [
                        "create",
                        {
                            question_id: this.pos.models["event.question"].get(
                                parseInt(questionId)
                            ),
                            value_answer_id: this.pos.models["event.question.answer"].get(
                                parseInt(answer)
                            ),
                        },
                    ]),
                });
            }
        }
    },
    onMouseDown(event, product) {
        if (product.event_id) {
            return;
        }
        return super.onMouseDown(event, product);
    },
    onTouchStart(product) {
        if (product.event_id) {
            return;
        }
        return super.onTouchStart(product);
    },
});
