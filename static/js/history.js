"use strict";
import {clear_array, last_element} from '/static/js/utils.js';


/**
 * Edit history container.
 */
export class History {
    constructor(maxlen=20) {
        this.tail = [];
        this.head = [];
        this.maxlen = maxlen;
    }

    get length() {
        return this.tail.length + this.head.length;
    }

    /**
     * History can be undone.
     */
    get undoable() {
        return this.tail.length > 1;
    }

    /**
     * History can be restored.
     */
    get redoable() {
        return this.head.length > 0;
    }

    /**
     * Limit history length to maxlen.
     */
    _limit() {
        while (this.tail.length > this.maxlen) {
            this.tail.shift();
        }
    }

    /**
     * Capture a new state and add it to the history. Will clear off head.
     */
    capture(state) {
        clear_array(this.head);
        this.tail.push(state);
        this._limit();
    }

    /**
     * Retrieve current state.
     */
    retrieve() {
        return last_element(this.tail);
    }

    /**
     * Wind back one state.
     */
    undo() {
        if (!this.undoable)
            throw "Nothing to undo!";

        const current = this.tail.pop();
        this.head.unshift(current);
        return this.retrieve();
    }

    /**
     * Rewind one state.
     */
    redo() {
        if (!this.redoable)
            throw "Nothing to redo!";

        const previous = this.head.shift();
        this.tail.push(previous);
        this._limit();
        return this.retrieve();
    }
}
