import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { deserializeDate } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

/**
 * Load the current user activities in the Attendee Calendar model.
 * Can be activated/deactivated using the "userActivitiesEnabled" getter.
 * Done using a patch to prevent loading this feature and the store service in POS.
 */
patch(AttendeeCalendarModel.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
    },

    /**
     * @override
     * Fetch the user activities from the systray into store.activityGroups
     */
    async load() {
        if (this.userActivitiesEnabled) {
            const data = await rpc(
                "/mail/data",
                { fetch_params: ["systray_get_activities"], context: user.context },
                { silent: true }
            );
            this.store.insert(data);
        }
        await super.load(...arguments);
    },

    get activities() {
        return this.data.activities;
    },

    /**
     * Whether or not to show the activities in the attendee calendar.
     * User preference controlled using a filter in the calendar side bar.
     */
    get showActivities() {
        return user.settings.calendar_default_show_activities;
    },

    /**
     * Override to control whether or not the current user can see and manage
     * their activities directly from the attendee calendar.
     * Activate/Deactivate the feature.
     **/
    get userActivitiesEnabled() {
        return true;
    },

    /**
     * Create a Full Calendar library event with the activities for the day.
     */
    createActivityEventAt(day, activities) {
        const event = {
            id: `activity-event-${day.toISODate()}`,
            colorIndex: user.partnerId || 0,
            duration: 1,
            start: day,
            end: day.plus({ hours: 1 }),
            isActivity: true,
            isAllDay: true,
            resModel: "mail.activity",
            rawRecord: activities,
        };
        if (activities.length > 1) {
            // Multiple activities for the day
            return {
                ...event,
                title: _t("%s pending activities", activities.length),
                isMultiActivity: true,
            };
        }
        // Single activity for the day
        return {
            ...event,
            title: activities[0].display_name,
            isMultiActivity: false,
        };
    },

    /**
     * Update the model activity data using the stored systray activities.
     */
    async updateActivityData(data) {
        if (!this.userActivitiesEnabled) {
            data.activities = {};
            return;
        }
        // Retrieves activities from the store
        const activityIds = this.store.activityGroups.flatMap((group) => group.activity_ids);
        if (!activityIds.length) {
            data.activities = {};
            return;
        }
        const activities = await this.orm.webSearchRead(
            "mail.activity",
            [["id", "in", activityIds]],
            {
                specification: {
                    can_write: {},
                    date_deadline: {},
                    display_name: {},
                    icon: {},
                },
            }
        );
        // Create activity events
        const activitiesPerDueDate = activities.records.reduce((acc, activity) => {
            const key = activity.date_deadline;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(activity);
            return acc;
        }, {});
        const activityEvents = {};
        for (const [date, activities] of Object.entries(activitiesPerDueDate)) {
            const activityEvent = this.createActivityEventAt(deserializeDate(date), activities);
            activityEvents[activityEvent.id] = activityEvent;
        }
        data.activities = activityEvents;
    },

    /**
     * @override
     */
    async updateData(data) {
        await super.updateData(...arguments);
        await this.updateActivityData(data);
    },
});
