/**
 * Editing history.
 *
 * @module js/history
 */
import { Deque } from "/static/js/deque.js";
import { last_element } from "/static/js/utils.js";


/**
 * Editing history container. Keeps track of changes in a `past` and `future`
 * queue. Allows for capturing new states and retrieving the current one. An
 * editing state can be an arbitrary JS object.
 *
 * @param {number} maxlen - Maximum lengths of past and future queues.
 */
export class History {
    constructor(maxlen = 20) {
        this.past = new Deque(0, maxlen);
        this.future = new Deque(0, maxlen);
    }

    /**
     * History length. Total number of states in past and future.
     * @type {number}
     */
    get length() {
        return this.past.length + this.future.length;
    }

    /**
     * Can history be made undone?
     * @type {boolean}
     */
    get undoable() {
        return this.past.length > 1;
    }

    /**
     * Can the wheel of time be turned back?
     * @type {boolean}
     */
    get redoable() {
        return this.future.length > 0;
    }

    /**
     * Are there unsaved changes?
     * @type {boolean}
     */
    get savable() {
        return this.length > 1;
    }

    /**
     * Capture a new state and add it to the history. This will clear the
     * future.
     *
     * @param {object} state - State to capture / add to history.
     */
    capture(state) {
        this.future.clear();
        this.past.push(state);
    }

    /**
     * Retrieve current state.
     *
     * @returns {object | null} current state (if any).
     */
    retrieve() {
        if (this.past.length === 0) {
            return null;
        }

        return last_element(this.past);
    }

    /**
     * Wind back one state.
     *
     * @returns {object} Newly current state.
     */
    undo() {
        if (!this.undoable) {
            throw "Nothing to undo!";
        }

        const current = this.past.pop();
        this.future.appendleft(current);
        return this.retrieve();
    }

    /**
     * Fast forward one state.
     *
     * @returns {object} Newly current state.
     */
    redo() {
        if (!this.redoable) {
            throw "Nothing to redo!";
        }

        const previous = this.future.popleft();
        this.past.push(previous);
        return this.retrieve();
    }

    /**
     * Clear entire history.
     */
    clear() {
        this.past.clear();
        this.future.clear();
    }
}
