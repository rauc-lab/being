/** 
 * @module components/plotter
 */
import { tick_space, } from "/static/js/layout.js";
import { array_min, array_max } from "/static/js/array.js";
import { divide_arrays} from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { Deque } from "/static/js/deque.js";
import { clip } from "/static/js/math.js";
import { cycle } from "/static/js/utils.js";
import { Widget, WidgetBase, append_template_to } from "/static/js/widget.js";


/** @const {array} - Default line colors */
const COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
];


/**
 * Line artist. Contains ring buffer for line data and knows how to draw
 * itself.
 *
 * @param {CanvasRenderingContext2D} ctx - Canvas rendering context.
 * @param {string} [color=#000000] - Line color.
 * @param {number} [maxlen=100] - Maximum number of data points.
 * @param {number} [lineWidth=2] - Line width.
 */
export class Line {
    constructor(ctx, color = "#000000", maxlen = 100, lineWidth = 2) {
        this.ctx = ctx;
        this.color = color;
        this.lineWidth = lineWidth;
        this.data = new Deque(0, maxlen);
    }

    /**
     * Get / set maxlen of buffer.
     * @type {number}
     */
    get maxlen() {
        return this.data.maxlen;
    }

    set maxlen(maxlen) {
        this.data.maxlen = maxlen;
    }

    /**
     * Number of data points.
     * @type {number}
     */
    get length() {
        return this.data.length;
    }


    /**
     * First data column.
     *
     * @returns {array} All x values.
     */
    get x_data() {
        return this.data.map(pt => pt[0]);
    }

    /**
     * Second data column.
     *
     * @returns {array} All y values.
     */
    get y_data() {
        return this.data.map(pt => pt[1]);
    }

    /**
     * Reset data buffer.
     */
    clear() {
        this.data.clear();
    }

    /**
     * Append new data point to data buffer.
     *
     * @param {array} pt - Data point to append.
     */
    append_data(pt) {
        this.data.append(pt);
    }

    /**
     * Calculate line width of Line artist.
     *
     * @returns {BBox} Data bounding box.
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
     * Draw line. Transforms have to be set from the outside.
     */
    draw() {
        if (this.length < 2) {
            return;
        }

        this.ctx.beginPath();
        let prevTime = Infinity;
        let prevValue = 0;
        this.data.forEach(pt => {
            if (pt[0] < prevTime) {
                this.ctx.moveTo(...pt);
            } else {
                this.ctx.lineTo(...pt);
            }

            prevTime = pt[0];
            prevValue = pt[1];
        });

        // Reset transform for proper line width
        this.ctx.save();
        this.ctx.resetTransform();
        this.ctx.lineWidth = this.lineWidth;
        this.ctx.strokeStyle = this.color;
        this.ctx.stroke();

        /*
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
        */
        this.ctx.restore();
    }
}


/** @const {String} - Plotter widget template */
const PLOTTER_TEMPLATE = `
<style>
    :host {
        display: flex;
        position: relative;
        border: 2px solid black;
        overflow: hidden;
    }

    svg {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
    }
</style>
<div>
<canvas id="canvas">
    Your browser doesn't support the HTML5 canvas tag.
</canvas>
<svg id="svg" xmlns="http://www.w3.org/2000/svg">
    Your browser doesn't support inline SVG.
</svg>
<span style="padding-left:1em">
<i>Double click anywhere to create new points. Hold shift down to side-scroll or scale.</i>
</span>
</div>
`;


/**
 * Data plotter widget.
 *
 * Holds a canvas / SVG with its own viewport bounding box. Manages data space
 * <-> view space transformations.
 */
export class Plotter extends WidgetBase {
    constructor(margin=50, minHeight=0.001) {
        super()
        this.margin = margin;
        this.minViewport = new BBox([Infinity, -minHeight], [-Infinity, minHeight]);
        this.autoscaling = true;
        this.viewport = new BBox([0, 0], [1, 1]);
        this.trafo = new DOMMatrix();
        this.trafoInv = new DOMMatrix();
        this.lines = new Map();
        this.colorPicker = cycle(COLORS);

        this.append_template(PLOTTER_TEMPLATE);
        this.canvas = this.shadowRoot.getElementById("canvas");
        this.svg = this.shadowRoot.getElementById("svg");

        this.ctx = this.canvas.getContext("2d");
        this.ctx.lineCap = "round";  //"butt" || "round" || "square";
        this.ctx.lineJoin = "round";  //"bevel" || "round" || "miter";

        this._maxlen = Infinity;
    }

    // Public

    /**
     * Get / set maxlen for all current and future lines.
     * @type {number}
     */
    get maxlen() {
        return this._maxlen;
    }

    set maxlen(value) {
        this._maxlen = value;
        this.lines.forEach(line => {
            line.maxlen = value;
        });
    }

    /**
     * Resize plotter. Adjust canvas size and recompute transformation
     * matrices.
     */
    resize() {
        this.canvas.width = this.clientWidth;
        this.canvas.height = this.clientHeight;
        this.update_transformation_matrices();
        this.draw();
    }

    /**
     * Transform a data point to view space.
     *
     * @param {array} pt - 2d data point.
     *
     * @returns {array} Transformed 2d point.
     */
    transform_point(pt) {
        const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
        return [ptHat.x, ptHat.y];
    }

    /**
     * Transform multiple data point into view space.
     *
     * @param {array} pts - Array of 2d data points.
     *
     * @returns {array} Array of 2d transformed points.
     */
    transform_points(pts) {
        return pts.map(pt => {
            const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
            return [ptHat.x, ptHat.y];
        });
    }

    /**
     * Coordinates of mouse event inside view space.
     *
     * @param {MouseEvent} evt - Mouse event to transform into data space.
     *
     * @returns {array} Coordinate point.
     */
    mouse_coordinates(evt) {
        const rect = this.canvas.getBoundingClientRect();
        const x = evt.clientX - rect.left;
        const y = evt.clientY - rect.top;
        const pt = (new DOMPoint(x, y)).matrixTransform(this.trafoInv);
        return [pt.x, pt.y];
    }

    /**
     * Create a new line artist for the given line number.
     *
     * @param {number} lineNr - Line number.
     */
    init_new_line(lineNr) {
        const newLine = new Line(this.ctx, this.colorPicker.next())
        newLine.maxlen = this._maxlen;
        this.lines.set(lineNr, newLine);
    }

    /**
     * Plot single new value.
     * 
     * @param {number} timestamp - Timestamp.
     * @param {number} value - Scalar value.
     * @param {number} lineNr - Line number to append new values to.
     */
    plot_value(timestamp, value, lineNr=0) {
        if (!this.lines.has(lineNr)) {
            this.init_new_line(lineNr);
        }

        this.lines.get(lineNr).append_data([timestamp, value]);
    }

    /**
     * Plot some new values. Get appended to current lines.
     *
     * @param {number} timestamp - Timestamp value.
     * @param {array} values - Values to plot.
     */
    plot_values(timestamp, values) {
        values.forEach((value, nr) => {
            this.plot_value(timestamp, value, nr);
        });
    }

    /**
     * Plot all values across time in a being state message.
     * 
     * @param {object} msg - Being state message.
     */
    plot_being_state_message(msg) {
        this.plot_values(msg.timestamp, msg.values);
        this.draw();
    }

    /**
     * Draw all line artists.
     */
    draw_lines() {
        this.lines.forEach(line => {
            line.draw();
        });
    }

    /**
     * Rescale and draw canvas.
     */
    draw_canvas() {
        if (this.autoscaling) {
            this.auto_scale();
        }

        this.clear_canvas();
        this.draw_axis_and_tick_labels();
        this.draw_lines();
    }

    /**
     * Draw everything
     */
    draw() {
        this.draw_canvas();
    }

    /**
     * Change viewport and redraw.
     *
     * @param {BBox} bbox - New viewport bounding box.
     */
    change_viewport(bbox) {
        if (!bbox.is_finite()) {
            return;
        }

        this.viewport = this.minViewport.copy();
        this.viewport.expand_by_bbox(bbox);
        this.update_transformation_matrices();
        this.draw();
    }

    /**
     * Expand viewport vertically and redraw.
     *
     * @param {number} ymin - Lower vertical bound.
     * @param {number} ymax - Upper vertical bound.
     */
    expand_viewport_vertically(ymin, ymax) {
        this.viewport.ll[1] = Math.min(this.viewport.ll[1], ymin);
        this.viewport.ur[1] = Math.max(this.viewport.ur[1], ymax);
        this.update_transformation_matrices();
        this.draw();
    }

    /**
     * Expand viewport by some other bounding box.
     *
     * @param {BBox} bbox - Bounding box.
     */
    expand_viewport_by_bbox(bbox) {
        if (!bbox.is_finite()) {
            return;
        }

        this.viewport.expand_by_bbox(bbox);
        this.update_transformation_matrices();
        this.draw();
    }

    /**
     * Make lines forget one value.
     */
    forget() {
        this.lines.forEach(line => line.data.popleft());
    }

    /**
     * Clear all lines.
     */
    clear_lines() {
        this.lines.forEach(line => line.data.clear());
    }

    // Private

    connectedCallback() {
        addEventListener("resize", () => this.resize());
        this.resize();
    }

    /**
     * Clear canvas.
     */
    clear_canvas() {
        this.ctx.save();
        this.ctx.resetTransform();
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.restore();
    }

    /**
     * Update viewport bounding box current line data.
     */
    auto_scale() {
        this.viewport = this.minViewport.copy();
        this.lines.forEach(line => {
            if (line.length > 0) {
                this.viewport.expand_by_bbox(line.calc_bbox());
            }
        });
        this.update_transformation_matrices();
    }

    /**
     * Update transformation matrices from current viewport.
     */
    update_transformation_matrices() {
        const width = this.clientWidth;
        const height = this.clientHeight;
        const [sx, sy] = divide_arrays(
            [width - 2 * this.margin, height - 2 * this.margin],
            this.viewport.size,
        );
        if (!isFinite(sx) || !isFinite(sy) || sx === 0 || sy === 0) {
            return;
        }

        // Data space -> Image view space
        this.trafo = DOMMatrix.fromMatrix({
            a: sx,
            d: -sy,
            e: -sx * this.viewport.ll[0] + this.margin,
            f: sy * (this.viewport.ll[1] + this.viewport.height) + this.margin,
        });

        // Image view space -> Data space
        this.trafoInv = this.trafo.inverse();
        this.ctx.setTransform(this.trafo);

        this.tick_space_x = tick_space(this.viewport.ll[0], this.viewport.ur[0]);
        this.tick_space_y = tick_space(this.viewport.ll[1], this.viewport.ur[1]);
    }

    /**
     * Draw axis and tick labels.
     *
     * @param {string} color - Axis and tick label color.
     */
    draw_axis_and_tick_labels(color = "silver") {
        const ctx = this.ctx;
        ctx.fillStyle = color;
        ctx.strokeStyle = color;

        // Draw axis
        ctx.save();
        ctx.resetTransform();
        ctx.beginPath();
        const origin = (new DOMPoint()).matrixTransform(this.trafo);

        // Round for crisper lines
        origin.x = Math.round(origin.x);
        origin.y = Math.round(origin.y);

        ctx.moveTo(this.margin, origin.y);
        ctx.lineTo(this.canvas.width - this.margin, origin.y);
        ctx.moveTo(origin.x, this.margin);
        ctx.lineTo(origin.x, this.canvas.height - this.margin);
        ctx.stroke();

        // Draw ticks
        const offset = 3;
        ctx.font = ".8em Helvetica";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";   // top, middle, bottom
        this.tick_space_x.forEach(x => {
            const pt = (new DOMPoint(x, 0)).matrixTransform(this.trafo);
            ctx.fillText(x, pt.x, clip(pt.y + offset, 0, this.canvas.height - this.margin));
        });
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";   // top, middle, bottom
        this.tick_space_y.forEach(y => {
            const pt = (new DOMPoint(0, y)).matrixTransform(this.trafo);
            ctx.fillText(y, clip(pt.x - offset, this.margin, this.canvas.width), pt.y);
        });

        ctx.restore();
    }
}

customElements.define("being-plotter", Plotter);
