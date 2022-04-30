/**
 * Some configuration values / definitions.
 *
 * @module js/config
 */


/** @const {string} - API url base address. */
export const API = location.origin + "/api";

/** @const {string} - Websocket address. */
export const WS_ADDRESS = ((location.protocol === "http:") ? "ws://" : "wss://") + location.host + "/stream";
