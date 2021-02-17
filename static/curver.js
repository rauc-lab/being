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
    setattr,
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

const MARGIN = 50;


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
}





/**
 * Curver base class for Plotter and Editor.
 */
class CurverBase extends HTMLElement {
    constructor(auto=true) {
        console.log("CurverBase.constructor");
        super();
        this.auto = auto;
        this.width = 1;
        this.height = 1;
        this.bbox = new BBox([0, 0], [1, 1]);
        this.trafo = new DOMMatrix();
        this.trafoInv = new DOMMatrix();
        this.lines = [];
        this.colorPicker = cycle(COLORS);
        this.init_elements();
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
        this.svg = svg;

        this.shadowRoot.append(link, this.canvas, this.svg, this.toolbar);
    }

    update_bbox() {
        this.bbox.reset();
        this.lines.forEach(line => {
            this.bbox.expand_by_bbox(line.calc_bbox());
        });
    }

    update_trafo() {
        const [sx, sy] = divide_arrays([this.width - 2 * MARGIN, this.height - 2 * MARGIN], this.bbox.size);
        if (!isFinite(sx) || !isFinite(sy) || sx === 0 || sy === 0)
            return

        this.trafo = DOMMatrix.fromMatrix({
            a: sx,
            d: -sy,
            e: -sx * this.bbox.ll[0] + MARGIN,
            f: sy * (this.bbox.ll[1] + this.bbox.height) + MARGIN,
        });
        this.trafoInv = this.trafo.inverse();
        this.ctx.setTransform(this.trafo);
        //this.svg.g.setAttribute("transform", this.trafo.toString());
    }

    /**
     * Resize elements. Mainly because of canvas because of lacking support for
     * relative sizes. Can be used as event handler with
     * `this.resize.bind(this)`.
     */
    resize() {
        //console.log("CurverBase.resize");
        this.canvas.width = this.width = this.clientWidth;
        this.canvas.height = this.height = this.clientHeight;

        // Flip y-axis
        //const mtrx = [1, 0, 0, -1, 0, this.height];
        //this.ctx.setTransform(...mtrx);

        //this.draw();
        this.update_trafo();
    }

    connectedCallback() {
        addEventListener("resize", evt => this.resize());
        this.resize();
        //this.run();
        //setTimeout(() => this.resize(), 1);
        setTimeout(() => {
            this.resize();
            this.run();
        },100);
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
     * Clear canvas.
     */
    clear_canvas() {
        this.ctx.save();
        this.ctx.resetTransform();
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.restore();
    }

    /**
     * Draw axis and tick labels.
     */
    draw_axis_and_tick_labels(color="silver") {
        const ctx = this.ctx;
        ctx.fillStyle = color;
        ctx.strokeStyle = color;

        // Draw axis
        ctx.save();
        ctx.resetTransform();
        ctx.beginPath();
        const origin = (new DOMPoint()).matrixTransform(this.trafo);

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
        tick_space(this.bbox.ll[0], this.bbox.ur[0]).forEach(x => {
            const pt = (new DOMPoint(x, 0)).matrixTransform(this.trafo);
            ctx.fillText(x, pt.x, origin.y + offset);
        });
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";   // top, middle, bottom
        tick_space(this.bbox.ll[1], this.bbox.ur[1]).forEach(y => {
            const pt = (new DOMPoint(0, y)).matrixTransform(this.trafo);
            ctx.fillText(y, origin.x - offset, pt.y);
        });

        ctx.restore();
    }

    /**
     * Draw single frame.
     */
    draw_lines() {
        if (this.auto) {
            this.update_bbox();
            this.update_trafo();
        }

        this.clear_canvas();
        this.draw_axis_and_tick_labels();
        this.lines.forEach(line => {
            line.draw();
        });
    }

    /**
     * Render continuous frames.
     */
    render(now) {
        this.draw_lines();
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
        rec.classList.add("btn-black")
        rec.innerHTML = "Rec";
        this.toolbar.appendChild(rec);
    }

}


customElements.define('being-plotter', Plotter);




function shift(data, offset) {
    return data.map(pt => {
        return [pt[0] + offset[0], pt[1] + offset[1]];
    })
}






/**
 * Spline editor.
 *
 * Shadow root with canvas and SVG overlay.
 */
class Editor extends CurverBase {
    constructor() {
        console.log("BeingCurver.constructor");
        const auto = false;
        super(auto);
        //this.history = new History();
    }

    resize() {
        super.resize();
        this.draw_spline();
    }

    transform_point(pt) {
        const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
        return [ptHat.x, ptHat.y];
    }
    
    transform_points(pts) {
        return pts.map(pt => {
            const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
            return [ptHat.x, ptHat.y];
        });
    }


    /**
     * Make SVG element draggable
     */
    make_draggable(ele) {
        /**
         * Transform mouse event into SVG space.
         */
        const pt = this.svg.createSVGPoint();
        const coords = evt => {
            pt.x = evt.clientX;
            pt.y = evt.clientY;
            let a = pt.matrixTransform(this.svg.getScreenCTM().inverse());
            let b = (new DOMPoint(a.x, a.y)).matrixTransform(this.trafoInv);
            return [b.x, b.y];
        };


        /** Start position of drag motion. */
        let start = null;
        let orig = [];


        /**
         * Start drag.
         */
        const start_drag = evt => {
            const pt = coords(evt);
            start = pt;
            orig = ele.data.slice();

            console.log("start_drag", start);

            addEventListener("mousemove", drag);
            addEventListener("mouseup", end_drag);
            addEventListener("mouseleave", end_drag);
        }

        ele.addEventListener("mousedown", start_drag);


        /**
         * Drag element.
         */
        const drag = evt => {
            const pt = coords(evt);
            const delta = subtract_arrays(pt, start);

            console.log("drag", delta);
            ele.data = shift(orig, delta);
            this.draw_spline();
        }

        /**
         * End dragging of element.
         */
        const end_drag = evt => {
            const pt = coords(evt);
            const delta = subtract_arrays(pt, start);

            console.log("end_drag", pt);

            removeEventListener("mousemove", drag);
            removeEventListener("mouseup", end_drag);
            removeEventListener("mouseleave", end_drag);
        }
    }

    load_spline(spline) {
        const cps = bpoly_to_bezier(spline);
        this.init_spline(cps);
    }

    init_path(pts, strokeWidth=1, color="black") {
        const path = draw_path(this.svg, pts, strokeWidth, color);
        path.data = pts;
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(path.data)));
        };
        return path
    }

    init_circle(pt, radius=1, color="black") {
        const circle = draw_circle(this.svg, pt, radius, color);
        circle.data = [pt];
        circle.draw = () => {
            const ptHat = (new DOMPoint(...circle.data[0])).matrixTransform(this.trafo);
            setattr(circle, "cx", ptHat.x);
            setattr(circle, "cy", ptHat.y);
        }
        return circle;
    }

    init_spline(cps, lw=2) {
        this.bbox = fit_bbox(cps.flat(1));
        this.update_trafo();
        remove_all_children(this.svg);
        cps.forEach((pts, i) => {
            let path = this.init_path(pts, lw);
            let knot = this.init_circle(pts[0], 3*lw);
            this.make_draggable(knot);
            const isLast = (i === cps.length - 1);
            if (isLast) {
                let knot = this.init_circle(last_element(pts), 3*lw);
            }
        });

        this.draw_spline();
    }

    draw_spline() {
        for (let ele of this.svg.children) {
            ele.draw();
        }
    }
}


customElements.define('being-editor', Editor);
