"use strict";
import {Flasher} from "/static/js/flasher.js";
import {MS} from "/static/js/constants.js";


const FLASHER = new Flasher();


/**
 * Try to receive data from web socket connection and hand over to data to
 * function handler. Repeatedly try to reconnect if connection dead. Assumes
 * JSON data.
 *
 * @param url to fetch color data for panels from.
 * @param callbacks type name -> callback dictionary.
 */
export function receive_from_websocket(url, callbacks, reconnectTimeout=1.) {
    const sock = new WebSocket(url);
    sock.onopen = function(evt) {
        console.log("Open socket connection", url);
        FLASHER.reset();
    };
    sock.onmessage = function(evt) {
        let obj = JSON.parse(evt.data);
        callbacks[obj.type].forEach(function(func) {
            func(obj);
        });
    };
    sock.onerror = function(evt) {
        //console.log("Socket error", evt);
        FLASHER.flash(evt);
        sock.close();
    };
    sock.onclose = function(evt) {
        console.log("Closed socket connection", evt);
        window.setTimeout(receive_from_websocket, reconnectTimeout*MS, url, callbacks);
    };
}
