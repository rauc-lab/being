"use strict";
import { create_element, setattr } from "/static/js/svg.js";


export const PAUSED = "PAUSED";
export const PLAYING = "PLAYING";
export const RECORDING = "RECORDING";


/** Valid state transitions. */
const Transitions = {
    PAUSED: [PLAYING, RECORDING],
    PLAYING: [PAUSED],
    RECORDING: [PAUSED],
}


/**
 * Transport / playback cursor container. Current playing position, duration,
 * looping, playing, cursor drawing.
 */
export class Transport {
    constructor(editor, looping=true) {
        this.editor = editor;
        this.state = PAUSED;
        this.looping = looping;
        this.position = 0;
        this.duration = 1;
        this.startTime = 0;
        this.latestTimestamp = 0;
        this._init_cursor();
    }

    get paused() {
        return this.state === PAUSED;
    }

    get playing() {
        return this.state === PLAYING;
    }

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
        this.editor.transportGroup.appendChild(line);
        this.cursor = line;
    }

    _change_state(newState) {
        if (Transitions[this.state].includes(newState)) {
            this.state = newState;
        }
    }

    pause() {
        this._change_state(PAUSED);
    }

    play() {
        this._change_state(PLAYING);
    }

    record() {
        this.startTime = this.latestTimestamp;
        this.duration = Infinity;
        this._change_state(RECORDING);
    }

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
     * Rewind cursor to the geginning.
     */
    rewind() {
        this.position = 0;
        this.draw_cursor();
    }

    /**
     * Draw SVG cursor line (update its attributes).
     */
    draw_cursor() {
        const [x, _] = this.editor.transform_point([this.position, 0]);
        setattr(this.cursor, "x1", x);
        setattr(this.cursor, "y1", 0);
        setattr(this.cursor, "x2", x);
        setattr(this.cursor, "y2", this.editor.height);
    }

    /**
     * Update transport position.
     */
    move(timestamp) {
        this.latestTimestamp = timestamp;
        let pos = timestamp - this.startTime;
        if (this.looping) {
            pos %= this.duration;
        }

        if (this.state !== PAUSED) {
            this.position = pos;
            this.draw_cursor(pos);
        }

        return pos;
    }
}
