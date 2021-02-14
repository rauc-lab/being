"use strict";


/**
 * Message flasher. Show message only once.
 * 
 * @param {function} print_func - Function to put messages to.
 */
export function Flasher(print_func=console.log) {
    let alreadyFlashed = new Set();

    /**
     * Flash message, but only once.
     * 
     * @param {string} msg - Message to flash.
     */
    this.flash = function(msg) {
        if (alreadyFlashed.has(msg))
            return;

        print_func(msg);
        alreadyFlashed.add(msg);
    };


    /**
     * Reset flashing. Rearm message flashing.
     */
    this.reset = function() {
        alreadyFlashed.clear();
    }
}
