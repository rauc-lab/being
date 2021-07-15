/**
 * Notification central.
 */
function _reclassify_notification(noti, newType) {
    const stuff = ["ajs-success", "ajs-error", "ajs-warning"];
    stuff.forEach(className => {
        noti.element.classList.remove(className)
    });
    noti.element.classList.add("ajs-" + newType);
}


/**
 * Notification central. Wrapper around alertify. Allows for persistent
 * notifications which can be resolved (with new message, type, wait time).
 */
export class NotificationCenter {
    constructor(alertify) {
        this.alertify = alertify;
        this.alertify.set("notifier", "position", "top-right");
        this.persistentNotifications = {};
    }

    notify_persistent(msg, type="message") {
        if (msg in this.persistentNotifications) {
            return;
        }

        const noti = this.alertify.notify(msg, type, 0.);
        this.persistentNotifications[msg] = noti;
    }

    resolve_persistent(msg, newMsg=null, newType="message", newWait=5) {
        if (newMsg === null) {
            newMsg = msg;
        }

        if (!(msg in this.persistentNotifications)) {
            return this.alertify.notify(newMsg, newType, newWait);
        }

        const noti = this.persistentNotifications[msg];
        delete this.persistentNotifications[msg];

        noti.setContent(newMsg);
        _reclassify_notification(noti, newType);
        noti.delay(newWait);
    }

    /*
    notify(msg, type="message", wait=5) {
        return this.alertify.notify(msg, type, wait);
    }
    */
}
