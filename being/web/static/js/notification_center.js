/**
 * Notification central.
 */
import { defaultdict } from "/static/js/utils.js";


/**
 * Remodel alertify notification object after it was created.
 *
 * @param {Object} noti Notificaiton object.
 * @param {String} msg New notification message text.
 * @param {String} type New notification type.
 * @param {Number} wait New notification wait time.
 */
export function remodel_notification(noti, msg=null, type=null, wait=null) {
    if (msg !== null) {
        noti.setContent(msg);
    }

    if (type !== null) {
        const stuff = ["ajs-success", "ajs-error", "ajs-warning"];
        stuff.forEach(className => {
            noti.element.classList.remove(className)
        });
        noti.element.classList.add("ajs-" + type);
    }

    if (wait !== null) {
        noti.delay(wait);
    }
}


/**
 * Number of items in an object.
 */
function object_size(obj) {
    let size = 0, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) {
            size++;
        }
    }

    return size;
}


/**
 * Notification central. Wrapper around alertify. Allows for persistent
 * notifications which can be resolved (with new message, type, wait time).
 */
export class NotificationCenter {
    constructor(alertify) {
        this.alertify = alertify;
        this.alertify.set("notifier", "position", "top-right");
        this.idCounter = 1;
        this.persistentNotifications = {};
        this.beenSaid = {};
        this.motorNotifications = defaultdict(Number);
        this.homingStates = defaultdict(Number);
    }

    /**
     * Notify message.
     *
     * @param {String} msg Message.
     * @param {String} type Notification type.
     * @param {Number} wait Auto-dismiss wait time.
     * @returns {Object} Notification object.
     */
    notify(msg, type="message", wait=2) {
        return this.alertify.notify(msg, type, wait);
    }

    /**
     * Notify persistent message.
     *
     * @param {String} msg Message.
     * @param {String} type Notification type.
     * @param {Number} wait Auto-dismiss wait time.
     * @returns {Number} Internal id of notification object.
     */
    notify_persistent(msg, type="message", wait=2, id=0) {
        if (msg in this.beenSaid) {
            return
        }

        if (id in this.persistentNotifications) {
            const noti = this.persistentNotifications[id];
            remodel_notification(noti, msg, type, wait);
        } else {
            id = this.idCounter++;
            const noti = this.alertify.notify(msg, type, wait, () => {
                delete this.beenSaid[id];
                delete this.persistentNotifications[id];
            });
            this.beenSaid[id] = msg;
            this.persistentNotifications[id] = noti;
        }

        return id;
    }

    /**
     * Process single motor message and update notifications.
     *
     * @param {Object} motor Motor object.
     */
    update_motor_notification(motor) {
        const homing = motor.homing.value;
        if (this.homingStates[motor.id] === homing) {
            return;
        }
        this.homingStates[motor.id] = homing;
        const name = motor.name;
        const notis = this.motorNotifications;
        switch(motor.homing.value) {
            case 0:
                notis[motor.id] = this.notify_persistent(name + " homing failed", "error", 0, notis[motor.id]);
                break;
            case 1:
                notis[motor.id] = this.notify_persistent(name + " unhomed", "warning", 0, notis[motor.id]);
                break;
            case 2:
                notis[motor.id] = this.notify_persistent(name + " homing ongoing", "warning", 0, notis[motor.id]);
                break;
            case 3:
                notis[motor.id] = this.notify_persistent(name + " homed", "success", 2, notis[motor.id]);
                break;
        }
    }

    new_motor_message(msg) {
        if (msg.type === "motor-update") {
            this.update_motor_notification(msg.motor);
        } else if (msg.type === "motor-updates") {
            msg.motors.forEach(motor => this.update_motor_notification(motor));
        } else if (msg.type === "motor-error") {
            const name = msg.motor.name;
            this.notify(name + " " + msg.message, "error", 5);
        } else {
            throw "Unsupported message type: " + msg.type;
        }
    }
}
