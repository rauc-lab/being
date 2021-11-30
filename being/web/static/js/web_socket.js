/**
 * @module web_socket Small web socket wrapper.
 */
import {MS} from "/static/js/constants.js";
import {defaultdict} from "/static/js/utils.js";


/**
 * Web socket central / relay. Try to receive data from web socket connection
 * and hand over to data to function handler. Repeatedly try to reconnect if
 * connection dead. Assumes Subscribe callbacks for message types. JSON data.
 *
 * @param url Web socket url to fetch data from.
 * @param reconnectTimeout Reconnect timeout duration in seconds.
 */
export class WebSocketCentral {
    constructor(url, reconnectTimeout=1.) {
        this.url = url;
        this.reconnectTimeout = reconnectTimeout;
        this.connected = false;
        this.callbacks = { "open": [], "close": [], }
        this.msgCallbacks = defaultdict(Array);
    }

    subscribe(event, callback) {
        this.callbacks[event].push(callback);
    }

    subscribe_to_message(msgType, callback) {
        this.msgCallbacks[msgType].push(callback);
    }

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
