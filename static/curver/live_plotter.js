"use strict";
/**
 * Live plotter custom HTML element.
 */
import { BBox } from "/static/js/bbox.js";
import { array_min, array_max } from "/static/js/math.js";
import { Deque } from "/static/js/deque.js";
import { CurverBase } from "/static/curver/curver.js";


/**
 * Line artist. Contains data ring buffer and knows how to draw itself.
 */
class Line {
    constructor(ctx, color = COLORS[0], maxlen = 1000, lineWidth = 2) {
        this.ctx = ctx;
        this._maxlen = maxlen;
        this.data = new Deque(0, maxlen);
        this.color = color;
        this.lineWidth = lineWidth;
    }


    /**
     * Get maxlen of buffer.
     */
    get maxlen() {
        return this.data.maxlen;
    }


    /**
     * Set maxlen of buffer and discard excess values.
     *
     * @param maxlen - New max length value.
     */
    set maxlen(maxlen) {
        this.data.maxlen = maxlen;
    }


    /**
     * First data column.
     */
    get x_data() {
        return this.data.map(pt => pt[0]);
    }


    /**
     * Second data column.
     */
    get y_data() {
        return this.data.map(pt => pt[1]);
    }


    /**
     * Calculate line width of Line artist.
     */
    calc_bbox() {
        // Data min / max
        const x = this.x_data;
        const y = this.y_data;
        const ll = [array_min(x), array_min(y)];
        const ur = [array_max(x), array_max(y)];
        return new BBox(ll, ur);
    }


    /**
     * Append new data point to data buffer.
     */
    append_data(pt) {
        this.data.append(pt);
    }


    /**
     * Draw line. Transforms have to be set from the outside.
     */
    draw() {
        if (this.data.length < 2)
            return

        const ctx = this.ctx;
        ctx.beginPath();
        let prev = Infinity;
        this.data.forEach(pt => {
            if (pt[0] < prev)
                ctx.moveTo(...pt);
            else
                ctx.lineTo(...pt);

            prev = pt[0];
        });
        ctx.save();
        ctx.resetTransform();
        ctx.lineWidth = this.lineWidth;
        ctx.strokeStyle = this.color;
        ctx.stroke();
        ctx.restore();
    }


    /**
     * Reset line data buffer.
     */
    clear() {
        this.data.clear();
    }
}


/**
 * Live plotter.
 */
class Plotter extends CurverBase {
    constructor() {
        super();
        this.recBtn = this.add_button("fiber_manual_record", "Record Motor", "btn-rec");
        this.recBtn.addEventListener("click", evt => this.record_signal(evt));
    }

    /**
     * Is currently recording property.
     */
    get recording() {
        // TODO: Good idea to store recording state in buttons checked attribute?
        return this.recBtn.hasAttribute("checked");
    }

    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            this.lines.push(new Line(this.ctx, color));
        }

        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([msg.timestamp, value]);
        });
    }

    /**
     * Record selected signal 
     */
    record_signal(el) {
        this.recBtn.toggleAttribute("checked");
    }
}


customElements.define('being-plotter', Plotter);