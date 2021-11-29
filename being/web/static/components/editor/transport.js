/**
 * @module transport Component for spline editor which manages transport state.
 */
import { create_element, setattr } from "/static/js/svg.js";
import { mod } from "/static/js/math.js";


// Note: We use string literals instead of the Object.freeze() enum trick so
// that we can use the states inside the Transitions table.
/** @const {string} Paused state. */
export const PAUSED = "PAUSED";

/** @const {string} Playing state. */
export const PLAYING = "PLAYING";

/** @const {string} Recording state. */
export const RECORDING = "RECORDING";

/** @const {object} Valid / possible state transitions. */
const Transitions = {
    PAUSED: [PLAYING, RECORDING],
    PLAYING: [PAUSED],
    RECORDING: [PAUSED],
};


/**
 * Transport / playback cursor container. Current playing position, duration,
 * looping, playing, cursor drawing.
 */
export class Transport {
    constructor(drawer, looping = true) {
        this.drawer = drawer;
        this.state = PAUSED;
        this.looping = looping;
        this.position = 0;  // TODO(atheler): Rename. It's not a position. It's a moment in time...
        this.duration = 1;
        this.startTime = 0;
        this.latestTimestamp = 0;
        this._init_cursor();
    }

    /**
     * @returns Is paused.
     */
    get paused() {
        return this.state === PAUSED;
    }

    /**
     * @returns Is playing.
     */
    get playing() {
        return this.state === PLAYING;
    }

    /**
     * @returns Is recording.
     */
    get recording() {
        return this.state === RECORDING;
    }

    /**
     * Initialize cursor SVG line.
     */
    _init_cursor() {
        const line = create_element("line");
        setattr(line, "stroke-width", 2);
        setattr(line, "stroke", "gray");
        this.drawer.svg.prepend(line);
        this.cursor = line;
    }

    /**
     * Change transport state (but only if valid transitions).
     * @param {string} newState New state.
     */
    _change_state(newState) {
        if (Transitions[this.state].includes(newState)) {
            this.state = newState;
        }
    }

    /**
     * Pause transport.
     */
    pause() {
        this._change_state(PAUSED);
    }

    /**
     * Start playing transport.
     */
    play() {
        this._change_state(PLAYING);
    }

    /**
     * Start recording transport.
     */
    record() {
        this.startTime = this.latestTimestamp;
        this.duration = Infinity;
        this._change_state(RECORDING);
    }

    /**
     * Stop transport.
     */
    stop() {
        this._change_state(PAUSED);
        this.rewind();
    }

    /**
     * Toggle looping.
     */
    toggle_looping() {
        this.looping = !this.looping;
    }

    /**
     * Rewind cursor to the beginning.
     */
    rewind() {
        this.position = 0;
        this.draw_cursor();
    }

    /**
     * Draw SVG cursor line (update its attributes).
     */
    draw_cursor() {
        const [x, _] = this.drawer.transform_point([this.position, 0]);
        setattr(this.cursor, "x1", x);
        setattr(this.cursor, "y1", 0);
        setattr(this.cursor, "x2", x);
        setattr(this.cursor, "y2", this.drawer.canvas.height);
    }

    /**
     * Update transport position.
     */
    move(timestamp) {
        this.latestTimestamp = timestamp;
        let pos = timestamp - this.startTime;
        if (this.looping) {
            pos = mod(pos, this.duration);
        }

        if (this.state !== PAUSED) {
            this.position = pos;
            this.draw_cursor(pos);
        }

        return pos;
    }
}
