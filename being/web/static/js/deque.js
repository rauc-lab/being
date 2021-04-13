/**
 * Deque array type with maxlen and better clearer naming (from Pythons
 * collections.deque).
 *
 * TODO(atheler): extend() / extendleft() methods?
 * TODO(atheler): Better constructor signature? Empty length vs. iterable vs. single item?
 */
export class Deque extends Array {
    constructor(iterable=0, maxlen=Infinity) {
        super(iterable);
        this._maxlen = maxlen;
        this._purge_left();
    }

    /**
     * Maximum length.
     */
    get maxlen() {
        return this._maxlen;
    }

    /**
     * Set new maximum length.
     */
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
     * Append items to the right.
     */
    append(...items) {
        this.push(...items);
        this._purge_left();
        return this.length;
    }

    /**
     * Append items to the left.
     */
    appendleft(...items) {
        this.unshift(...items);
        this._purge_right();
        return this.length;
    }

    /**
     * Pop item from the left side.
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
