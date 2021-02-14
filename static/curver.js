"use strict";
/**
 * Curver widgets. Live plotter and spline editor.
 */
import { BBox, fit_bbox, } from "/static/js/bbox.js";
import { bpoly_to_bezier, } from "/static/js/bezier.js";
import { History, } from "/static/js/history.js";
import { tick_space, } from "/static/js/layout.js";
import {
    add_arrays,
    array_max,
    array_min,
    divide_arrays,
    multiply_scalar,
    round,
    subtract_arrays,
} from "/static/js/math.js";
import {
    create_circle,
    create_element,
    create_line,
    create_path,
    draw_circle,
    draw_line,
    draw_path,
    path_d,
} from "/static/js/svg.js";
import { clear_array, cycle, last_element, remove_all_children, } from "/static/js/utils.js";


/** Degree enum-ish */
const Degree = Object.freeze({
    "CUBIC": 3,
    "QUADRATIC": 2,
    "LINEAR": 1,
});

/** Milliseconds to seconds factor */
const MS = 1000;

/** Default line colors */
const COLORS = [
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f',
    '#bcbd22',
    '#17becf',
];


/**
 * Line artist. Contains data ring buffer and knows how to draw itself.
 */
class Line {
    constructor(ctx, color=COLORS[0], maxlen=1000, lineWidth=2) {
        this.ctx = ctx;
        this._maxlen = maxlen;
        this.data = [];
        this.color = color;
        this.lineWidth = lineWidth;
    }

    /**
     * Get maxlen of buffer.
     */
    get maxlen() {
        return this._maxlen;
    }

    /**
     * Set maxlen of buffer and discard excess values.
     */
    set maxlen(value) {
        this._maxlen = value;
        this.purge();
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
     * Roll data to appropriate length.
     */
    purge() {
        while (this.data.length > this.maxlen) {
            this.data.shift();
        }
    }

    /**
     * Append new data point to data buffer.
     */
    append_data(pt) {
        this.data.push(pt);
        this.purge();
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
                ctx.moveTo(...pt)
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
}


/**
 * Curver base class for Plotter and Editor.
 */
class CurverBase extends HTMLElement {
    constructor() {
        console.log("CurverBase.constructor");
        super();
        this.width = 1;
        this.height = 1;
        this.lines = [];
        this.init_elements();
        this.colorPicker = cycle(COLORS);
    }

    /**
     * Current plotter size.
     */
    get size() {
        return [this.width, this.height];
    }

    /**
     * Initialize DOM elements with shadow root.
     */
    init_elements() {
        this.attachShadow({mode: "open"});

        // Apply external styles to the shadow dom
        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/curver.css");

        // Toolbar
        this.toolbar = document.createElement("div");
        this.toolbar.classList.add("toolbar");

        // Canvas
        this.canvas = document.createElement("canvas");
        this.ctx = this.canvas.getContext("2d");
        this.ctx.lineCap = "round";  //"butt" || "round" || "square";
        this.ctx.lineJoin = "round";  //"bevel" || "round" || "miter";

        // SVG
        const svg = create_element("svg");
        svg.g = svg.appendChild(create_element("g"))
        svg.g.spline = svg.g.appendChild(create_element("g"))
        this.svg = svg;
        this.shadowRoot.append(this.svg);

        this.shadowRoot.append(link, this.canvas, this.svg, this.toolbar);
    }

    /**
     * Resize elements. Mainly because of canvas because of lacking support for
     * relative sizes. Can be used as event handler with
     * `this.resize.bind(this)`.
     */
    resize() {
        console.log("CurverBase.resize");
        this.canvas.width = this.width = this.clientWidth;
        this.canvas.height = this.height = this.clientHeight;

        // Flip y-axis
        //const mtrx = [1, 0, 0, -1, 0, this.height];
        //this.ctx.setTransform(...mtrx);

        //this.draw();
    }

    connectedCallback() {
        addEventListener("resize", evt => this.resize());
        this.resize();
        //setTimeout(() => this.resize(), 1);
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
     * Calculate data bounding box.
     */
    calc_bbox() {
        let bbox = new BBox();
        this.lines.forEach((line, nr) => {
            if (nr !== 0)
                bbox.expand_by_bbox(line.calc_bbox());
        });
        return bbox;
    }

    compute_tranform_matrix(bbox, margin=50) {
        const [sx, sy] = divide_arrays([this.width-2*margin, this.height-2*margin], bbox.size);
        return DOMMatrix.fromMatrix({
            m11: sx,
            m22: -sy,
            m41: -sx * bbox.ll[0] + margin,
            m42: sy * (bbox.ll[1] + bbox.height) + margin,
        });
    }

    /**
     * Clear canvas.
     */
    clear() {
        this.ctx.resetTransform();
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    /**
     * Draw axis and tick labels.
     */
    draw_axis_and_tick_labels(bbox, mtrx, color="darkgray") {
        const ctx = this.ctx;
        ctx.fillStyle = color;
        ctx.strokeStyle = color;

        // Draw axis
        ctx.save();
        ctx.resetTransform();
        ctx.beginPath();
        const origin = (new DOMPoint()).matrixTransform(mtrx);

        // Round for crispr lines
        origin.x = Math.round(origin.x);
        origin.y = Math.round(origin.y);

        ctx.moveTo(0, origin.y);
        ctx.lineTo(this.width, origin.y);
        ctx.moveTo(origin.x, 0);
        ctx.lineTo(origin.x, this.height);
        ctx.stroke();

        // Draw ticks
        const offset = 3;
        ctx.font = ".8em Helvetica";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";   // top, middle, bottom
        tick_space(bbox.ll[0], bbox.ur[0]).forEach(x => {
            const pt = (new DOMPoint(x, 0)).matrixTransform(mtrx);
            ctx.fillText(x, pt.x, origin.y + offset);
        });
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";   // top, middle, bottom
        tick_space(bbox.ll[1], bbox.ur[1]).forEach(y => {
            const pt = (new DOMPoint(0, y)).matrixTransform(mtrx);
            ctx.fillText(y, origin.x - offset, pt.y);
        });

        ctx.restore();
    }

    /**
     * Draw single frame.
     */
    draw() {
        const bbox = this.calc_bbox();
        const mtrx = this.compute_tranform_matrix(bbox);
        this.clear();
        this.ctx.setTransform(mtrx);
        this.draw_axis_and_tick_labels(bbox, mtrx);
        this.lines.forEach(line => {
            line.draw();
        });
    }

    /**
     * Render continuous frames.
     */
    render(now) {
        this.draw();
        window.requestAnimationFrame(now => this.render(now));
    }

    /**
     * Start rendering.
     */
    run() {
        requestAnimationFrame(now => this.render(now));
    }
}


/**
 * Live plotter.
 */
class Plotter extends CurverBase {
    constructor() {
        super();
        const rec = document.createElement("button");
        rec.innerHTML = "Rec";
        this.toolbar.appendChild(rec);
    }

}


customElements.define('being-plotter', Plotter);


/**
 * Spline editor.
 *
 * Shadow root with canvas and SVG overlay.
 */
class Editor extends CurverBase {
    constructor() {
        console.log("BeingCurver.constructor");
        super();
        this.updateBbox = true;
        this.history = new History();
    }


        /*
    resize() {
        console.log("Plotter.resize");
        this.canvas.width = this.width = this.clientWidth;
        this.canvas.height = this.height = this.clientHeight;

        // Flip y-axis
        const mtrx = [1, 0, 0, -1, 0, this.height];
        this.ctx.setTransform(...mtrx);
        this.svg.g.setAttribute("transform", "matrix(" + mtrx.join(" ") + ")");
    }
    */


    new_data(msg) {
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            this.lines.push(new Line(this.ctx, color));
        }

        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([msg.timestamp % 9, value]);
        });
    }

    load_spline(spline) {
        console.log("load_spline");
        const cps = bpoly_to_bezier(spline);
        this.history.capture(cps);
        this.draw_spline();
    }


    draw_spline(lw=2, cw=6) {
        console.log('draw_spline()');
        if (!this.history.length) {
            return;
        }

        const cps = this.history.retrieve();
        const bbox = fit_bbox(cps.flat(1));
        const trafo = this.transformation_matrix(bbox);

        const area = this.svg.g.spline;
        remove_all_children(area)
        //spline_it(cps, area, trafo);

        cps.forEach(function(pts, i) {
            const color = "black";
            pts = transform(pts, trafo);

            // Path
            draw_path(area, pts, lw, color);

            // Knots
            draw_circle(area, pts[0], cw, color);
            if (i === cps.length - 1) {
                draw_circle(area, last_element(pts), cw, color);
            }

            // Control points and helper lines
            const order = pts.length;
            const degree = order - 1
            if (degree == Degree.QUADRATIC) {
                draw_line(area, pts[0], pts[1], lw, 'black');
                draw_circle(area, pts[1], cw, 'red');

            } else if (degree == Degree.CUBIC) {
                draw_line(area, pts[0], pts[1], lw, 'black');
                draw_line(area, pts[2], pts[3], lw, 'black');
                draw_circle(area, pts[1], cw, 'red');
                draw_circle(area, pts[2], cw, 'red');
            }
        });
    }
}


customElements.define('being-editor', Editor);
