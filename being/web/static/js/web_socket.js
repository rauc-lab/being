/**
 * @module web_socket Small web socket wrapper.
 */
import {MS} from "/static/js/constants.js";


const WEB_SOCKET_DOWN_MESSAGE = "WebSocket connection down";
const WEB_SOCKET_UP_MESSAGE = "WebSocket connection up and running";


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
        notificationCenter.resolve_persistent(
            WEB_SOCKET_DOWN_MESSAGE,
            WEB_SOCKET_UP_MESSAGE,
            "success",
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
        notificationCenter.notify_persistent(
            WEB_SOCKET_DOWN_MESSAGE,
            "error"
        );
        window.setTimeout(receive_from_websocket, reconnectTimeout*MS, url, callbacks, notificationCenter);
    };
}
