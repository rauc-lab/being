/**
 * Double ended queue.
 * @module js/deque
 */


/**
 * Deque array type with maxlen and better clearer naming (similar Pythons
 * collections.deque). Note that maxlen only takes effect when using the extra
 * methods but not the build in Array ones!
 * @param {number} [iterable=0] - Number of initial empty elements.
 * @param {number} [maxlen=Infinity] - Maximum length of deque.
 * @todo extend() / extendleft() methods?
 * @todo Better constructor signature? Empty length vs. iterable vs. single item?
 *
 * @example
 * maxlen = 3
 * queue = new Deque(0, maxlen);
 * queue.append(0, 1, 2, 3, 4);
 * // returns Deque(3) [2, 3, 4, _maxlen: 3]
 * console.log(queue);
 */
export class Deque extends Array {
    constructor(iterable=0, maxlen=Infinity) {
        super(iterable);
        this._maxlen = maxlen;
        this._purge_left();
    }

    /**
     * Get / set maximum length.
     * @type {number}
     */
    get maxlen() {
        return this._maxlen;
    }

    set maxlen(value) {
        this._maxlen = value;
        this._purge_left();
    }

    /**
     * Pop from left side until maxlen.
     */
    _purge_left() {
        while (this.length > this._maxlen) {
            this.shift();
        }
    }

    /**
     * Pop from right side until maxlen.
     */
    _purge_right() {
        while (this.length > this._maxlen) {
            this.pop();
        }
    }

    /**
     * Append items to the right side.
     * @returns {number} New deque length.
     */
    append(...items) {
        this.push(...items);
        this._purge_left();
        return this.length;
    }

    /**
     * Append items to the left side.
     * @returns {number} New deque length.
     */
    appendleft(...items) {
        this.unshift(...items);
        this._purge_right();
        return this.length;
    }

    /**
     * Pop item from the left side.
     * @returns {object} Popped item.
     */
    popleft() {
        return this.shift();
    }

    /**
     * Clear all items.
     */
    clear() {
        this.length = 0;
    }
}
