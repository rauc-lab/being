/**
 * @module web_socket Small web socket wrapper.
 */
import {MS} from "/static/js/constants.js";


let NOTIFICATION_ID = 0;


/**
 * Try to receive data from web socket connection and hand over to data to
 * function handler. Repeatedly try to reconnect if connection dead. Assumes
 * JSON data.
 *
 * @param url Web socket url to fetch data from.
 * @param callbacks Message type name -> Callback functions.
 * @param notificationCenter Notification instance to notify about web socket
 *     down or up and running again.
 * @param reconnectTimeout Reconnect timeout duration in seconds.
 */
export function receive_from_websocket(url, callbacks, notificationCenter, reconnectTimeout=1.) {
    const sock = new WebSocket(url);
    sock.onopen = function() {
        NOTIFICATION_ID = notificationCenter.notify_persistent(
            "Connected to Being",
            "success",
            2,
            NOTIFICATION_ID,
        );
    };
    sock.onmessage = function(evt) {
        let msg = JSON.parse(evt.data);
        callbacks[msg.type].forEach(function(func) {
            func(msg);
        });
    };
    sock.onerror = function() {
        sock.close();
    };
    sock.onclose = function() {
        NOTIFICATION_ID = notificationCenter.notify_persistent(
            "Being offline",
            "error",
            0,
            NOTIFICATION_ID,
        );
        window.setTimeout(
            receive_from_websocket,
            reconnectTimeout * MS,
            url,
            callbacks,
            notificationCenter,
        );
    };
}
