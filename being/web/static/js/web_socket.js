/**
 * @module web_socket Small web socket wrapper.
 */
import {MS} from "/static/js/constants.js";
import {remodel_notification} from "/static/js/notification_center.js";


const WEB_SOCKET_DOWN_MESSAGE = "WebSocket connection down";
const WEB_SOCKET_UP_MESSAGE = "WebSocket connection up and running";


let NOTIFICATION_ID = 0;


/**
 * Try to receive data from web socket connection and hand over to data to
 * function handler. Repeatedly try to reconnect if connection dead. Assumes
 * JSON data.
 *
 * @param url to fetch color data for panels from.
 * @param callbacks type name -> callback dictionary.
 */
export function receive_from_websocket(url, callbacks, notificationCenter, reconnectTimeout=1.) {
    const sock = new WebSocket(url);
    sock.onopen = function() {
        NOTIFICATION_ID = notificationCenter.notify_persistent(
            "WebSocket connection up and running",
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
    sock.onerror = function(evt) {
        sock.close();
    };
    sock.onclose = function(evt) {
        NOTIFICATION_ID = notificationCenter.notify_persistent(
            "WebSocket connection down",
            "error",
            0,
            NOTIFICATION_ID,
        );
        window.setTimeout(receive_from_websocket, reconnectTimeout*MS, url, callbacks, notificationCenter);
    };
}
