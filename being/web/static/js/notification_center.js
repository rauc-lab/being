export class NotificationCenter {
    constructor(alertify) {
        this.alertify = alertify;
        alertify.set("notifier", "position", "top-right");
        var notification = alertify.notify(
            "NotificationCenter sample message",
            "success",
            5,
        );
    }

    new_motor_message(msg) {
        console.log('msg:', msg)
    }
}
