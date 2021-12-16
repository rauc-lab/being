/**
 * Small web socket wrapper.
 * @module js/web_socket
 */
import {MS} from "/static/js/constants.js";
import {defaultdict} from "/static/js/utils.js";


/**
 * Web socket central / relay. Try to receive data from web socket connection
 * and hand over to data to function handler. Repeatedly try to reconnect if
 * connection dead. Assumes Subscribe callbacks for message types. JSON data.
 *
 * @param {string} url - Web socket url to fetch data from.
 * @param {number} reconnectTimeout - Reconnect timeout duration in seconds. Default is 1.0 seconds.
 */
export class WebSocketCentral {
    constructor(url, reconnectTimeout=1.0) {
        this.url = url;
        this.reconnectTimeout = reconnectTimeout;
        this.connected = false;
        this.callbacks = { "open": [], "close": [], }
        this.msgCallbacks = defaultdict(Array);
    }

    /**
     * Subscribe callback to WebSocket event.
     *
     * @param {string} event - Event name. ``"open"`` or ``"close"``.
     * @param {function} callback - Notificaiton callback function.
     */
    subscribe(event, callback) {
        this.callbacks[event].push(callback);
    }

    /**
     * Subscribe callback for messages of a given type.
     * 
     * @param {string} msgType - Message type to get notifications for.
     * @param {function} callback - Notificaiton callback function.
     */
    subscribe_to_message(msgType, callback) {
        this.msgCallbacks[msgType].push(callback);
    }

    /**
     * Try to connect. If ``reconnectTimeout`` is set will continously try to reconnect.
     */
    connect() {
        const sock = new WebSocket(this.url);
        sock.onopen = evt => {
            if (!this.connected) {
                this.connected = true;
                this.callbacks["open"].forEach(callback => {callback()})
            }
        };
        sock.onmessage = evt => {
            let msg = JSON.parse(evt.data);
            this.msgCallbacks[msg.type].forEach(function(func) {
                func(msg);
            });
        };
        sock.onerror = evt => {
            sock.close();
        };
        sock.onclose = evt => {
            if (this.connected) {
                this.connected = false;
                this.callbacks["close"].forEach(callback => {callback()})
            }

            if (this.reconnectTimeout !== null) {
                window.setTimeout(() => {
                    this.connect()
                }, this.reconnectTimeout * MS);
            }
        };
    }
}
