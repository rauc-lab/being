/** Main loop interval of being block network. */
export const INTERVAL = 0.010;

/** API address */
export const API = location.origin + "/api";

/** Websocket address */
export const WS_ADDRESS = ((location.protocol === "http:") ? "ws://" : "wss://") + location.host + "/stream";