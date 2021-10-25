/**
 * @module line Plotting line artist.
 */
import { BBox } from "/static/js/bbox.js";
import { array_min, array_max } from "/static/js/array.js";
import { Deque } from "/static/js/deque.js";
import { last_element } from "/static/js/utils.js";



/**
 * Line artist. Contains data ring buffer and knows how to draw itself.
 */
export class Line {
    constructor(editor, color = "#000000", maxlen = 1000, lineWidth = 2) {
        this.editor = editor;
        this.canvas = editor.canvas;
        this.ctx = editor.ctx;

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
        if (this.data.length < 2) {
            return;
        }

        const ctx = this.ctx;
        ctx.beginPath();
        let prevTime = Infinity;
        let prevValue = 0;
        this.data.forEach(pt => {
            if (pt[0] < prevTime) {
                ctx.moveTo(...pt);
            } else {
                ctx.lineTo(...pt);
            }

            prevTime = pt[0];
            prevValue = pt[1];
        });

        ctx.save();
        ctx.resetTransform();
        ctx.lineWidth = this.lineWidth;
        ctx.strokeStyle = this.color;
        ctx.stroke();

        const lastPt = [prevTime, prevValue];
        const [_, y] = this.editor.transform_point(lastPt);
        ctx.fillStyle = this.color;
        ctx.fillRect(
            this.canvas.width - 50,
            y - this.lineWidth,
            50,
            2*this.lineWidth,
        );
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
