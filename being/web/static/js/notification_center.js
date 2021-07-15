/**
 * Notification central.
 */
import { defaultdict } from "/static/js/utils.js";


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
    }

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

    process_motor(motor) {
        const notis = this.motorNotifications;
        const prefix = "Motor " + motor.id + " ";
        switch(motor.homing.value) {
            case 0:
                notis[motor.id] = this.notify_persistent(prefix + "unhomed", "warning", 0, notis[motor.id]);
                break;
            case 1:
                notis[motor.id] = this.notify_persistent(prefix + "homed", "success", 2, notis[motor.id]);
                break;
            case 2:
                notis[motor.id] = this.notify_persistent(prefix + "homing ongoing", "warning", 0, notis[motor.id]);
                break;
            case 3:
                notis[motor.id] = this.notify_persistent(prefix + "homing failed", "error", 0, notis[motor.id]);
                break;
        }
    }

    new_motor_message(msg) {
        if (msg.type === "motor-update") {
            this.process_motor(msg);
        } else if (msg.type === "motor-updates") {
            msg.motors.forEach(motor => this.process_motor(motor));
        } else {
            throw "Unsupported message type: " + msg.type;
        }
    }
}
