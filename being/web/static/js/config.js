/**
 * Some configuration values / definitions.
 *
 * @module js/config
 */


/**
 * @const {number} - Main loop interval of being block network.
 *
 * @deprecated Should be loaded from backend via API.
 */
export const INTERVAL = 0.010;

/** @const {string} - API url base address. */
export const API = location.origin + "/api";

/** @const {string} - Websocket address. */
export const WS_ADDRESS = ((location.protocol === "http:") ? "ws://" : "wss://") + location.host + "/stream";
