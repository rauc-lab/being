/**
 * @module config Some basic configurations.
 */


/** @const {number} - Main loop interval of being block network. */
export const INTERVAL = 0.010;

/** @const {string} - API address. */
export const API = location.origin + "/api";

/** @const {string} - Websocket address. */
export const WS_ADDRESS = ((location.protocol === "http:") ? "ws://" : "wss://") + location.host + "/stream";