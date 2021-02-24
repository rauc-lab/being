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
    mod,
    multiply_scalar,
    round,
    subtract_arrays,
    distance,
    cartesian_to_polar,
    polar_to_cartesian,
    clip,
} from "/static/js/math.js";
import {
    create_element,
    draw_circle,
    draw_line,
    draw_path,
    path_d,
    setattr,
} from "/static/js/svg.js";
import {
    arrays_equal,
    clear_array,
    cycle,
    deep_copy,
    last_element,
    remove_all_children,
} from "/static/js/utils.js";
import {Deque} from "/static/js/deque.js";
import {
    Degree,
    MS,
    Order,
    TAU,
    PI,
} from "/static/js/constants.js";


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
const INTERVAL = 0.010 * 1.2;
const PT = create_element("svg").createSVGPoint();


/**
 * Line artist. Contains data ring buffer and knows how to draw itself.
 */
class Line {
    constructor(ctx, color=COLORS[0], maxlen=1000, lineWidth=2) {
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
     */
    set maxlen(value) {
        this.data.maxlen = value;
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

    clear() {
        this.data.clear();
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
        this.ctmInv = this.svg.getScreenCTM().inverse();

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

        // Round for crisper lines
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
}


customElements.define('being-plotter', Plotter);


function dst_add(a, b, dst) {
    for (let i=0; i<a.length; i++)
        dst[i] = a[i] + b[i];
}


function dst_shift(pts, delta, dst) {
    for (let i=0; i<pts.length; i++) {
        dst[i][0] = pts[i][0] + delta[0];
        dst[i][1] = pts[i][1] + delta[1];
    }
}


function filter_undefined(arr) {
    return arr.filter(ele => ele !== undefined);
}


function designate(pt, dst) {
    for (let i=0; i<pt.length; i++)
        dst[i] = pt[i];
}


function point_mirror(pt, focal) {
    return [
        2 * focal[0] - pt[0],
        2 * focal[1] - pt[1],
    ]
}


function rotate_point_mirror(pt, focal, other) {
    const [_, angle] = cartesian_to_polar(subtract_arrays(focal, pt));
    const radius = distance(other, focal);
    return add_arrays(focal, polar_to_cartesian([radius, angle]));
}


function assert(condition, message="") {
    if (!condition)
        throw ("AssertionError " + message).trim();
}


/**
 * Check if array index corresponds to a knot data point in the data array.
 */
function is_knot(idx, degree) {
    return (idx % degree == 0);
}


/**
 * Get min / max editing boundary for cubic knot.
 * @param pts - Control points array
 * @param i - Knot index.
 */
function cubic_knot_boundaries(pts, i) {
    //const isKnot = (i % Degree.CUBIC == 0);
    const isKnot = is_knot(i, Degree.CUBIC);
    assert(isKnot, "Index " + i + " is not a cubic knot!");


    // Left boundary
    let xmin = -Infinity;
    if (i > 0) {
        const leftHeadroom = Math.min(
            pts[i][0] - pts[i-2][0],
            pts[i-1][0] - pts[i-3][0],
        )
        xmin = pts[i][0] - leftHeadroom;
    }


    // Right boundary
    let xmax = Infinity;
    if (i < pts.length - Degree.CUBIC) {
        const rightHeadroom = Math.min(
            pts[i+2][0] - pts[i][0],
            pts[i+3][0] - pts[i+1][0],
        )
        xmax = pts[i][0] + rightHeadroom;
    }

    return [xmin, xmax];
}


function cubic_control_point_boundaries(pts, i) {
    const isKnot = (i % Degree.CUBIC == 0);
    assert(!isKnot, "Index " + i + " is not a cubic control point!");
    const leftKnot = pts[Math.floor(i / Degree.CUBIC) * Degree.CUBIC];
    const rightKnot = pts[Math.ceil(i / Degree.CUBIC) * Degree.CUBIC];
    return [leftKnot[0], rightKnot[0]];
}


/**
 * Get [xmin, xmax] boundaries for a given curve point.
 */
function point_boundaries(pts, i, degree) {
    let xmin = -Infinity;
    let xmax = Infinity;

    if (0 <= i && i < pts.length) {
        switch (degree) {
            //case Degree.CONSTANT:
            //    break;
            case Degree.LINEAR:
                break;
            case Degree.CUBIC:
                break;
            default:
                throw "point_boundaries() does not support degree " + degree + "!";
        }
    }

    return [xmin, xmax];
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
        this.history = new History();
        this.duration = 1;
        this.maxlen = 1;
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


    grow_bbox(pt) {
        // TODO: Last update, limit grow rate
        this.bbox.expand_by_point(pt);
        this.update_trafo();
    }


    init_path(pts, strokeWidth=1, color="black") {
        const path = draw_path(this.svg, pts, strokeWidth, color);
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(pts)));
        };
        return path
    }


    init_circle(pt, radius=1, color="black") {
        const circle = draw_circle(this.svg, pt, radius, color);
        circle.draw = () => {
            const a = this.transform_point(pt);
            setattr(circle, "cx", a[0]);
            setattr(circle, "cy", a[1]);
        }
        return circle;
    }


    init_line(start, end, strokeWidth=1, color="black") {
        const line = draw_line(this.svg, start, end, strokeWidth, color);
        line.draw = () => {
            const a = this.transform_point(start);
            const b = this.transform_point(end);
            setattr(line, "x1", a[0]);
            setattr(line, "y1", a[1]);
            setattr(line, "x2", b[0]);
            setattr(line, "y2", b[1]);
        };
        return line;
    }


    /**
     * Coordinates of mouse event inside canvas / SVG data space.
     */
    mouse_coordinates(evt) {
        PT.x = evt.clientX;
        PT.y = evt.clientY;
        let a = PT.matrixTransform(this.ctmInv);
        let b = (new DOMPoint(a.x, a.y)).matrixTransform(this.trafoInv);
        return [b.x, b.y];
    }


    load_spline(spline) {
        this.degree = spline.coefficients[0].length;
        this.order = this.degree + 1;
        this.history.clear();
        const cps = bpoly_to_bezier(spline);
        this.workingCopy = cps;
        this.init_spline();
    }


    set_duration(duration) {
        console.log("duration:", duration);
        this.duration = duration;
        this.lines.forEach(line => {
            line.maxlen = this.duration / INTERVAL
        });
    }


    make_draggable(ele, drag, end_drag, xmin=-Infinity, xmax=Infinity) {
        /** Start position of drag motion. */
        let start = null;

        /**
         * Start drag.
         */
        const _start_drag = evt => {
            start = this.mouse_coordinates(evt);
            addEventListener("mousemove", _drag);
            addEventListener("mouseup", _end_drag);
            addEventListener("mouseleave", _end_drag);
        }

        ele.addEventListener("mousedown", _start_drag);

        /**
         * Drag element.
         */
        const _drag = evt => {
            const pt = this.mouse_coordinates(evt);
            const end = [clip(pt[0], xmin, xmax), pt[1]];
            const delta = subtract_arrays(end, start);
            drag(delta);
        }

        /**
         * End dragging of element.
         */
        const _end_drag = evt => {
            const end = this.mouse_coordinates(evt);
            if (arrays_equal(start, end))
                return;

            removeEventListener("mousemove", _drag);
            removeEventListener("mouseup", _end_drag);
            removeEventListener("mouseleave", _end_drag);

            end_drag(end);
        }
    }


    /**
     * Initialize spline elements.
     * @param cps - Control point tensor.
     */
    init_spline(lw=2) {
        const pts = this.workingCopy;
        this.bbox = fit_bbox(pts);
        this.update_trafo();
        this.lines.forEach(line => line.clear());
        const duration = last_element(pts)[0] - pts[0][0];
        this.set_duration(duration)
        remove_all_children(this.svg);

        switch (this.order) {
            case Order.CUBIC:
                return this.init_cubic_spline(lw);
            case Order.QUADRATIC:
                throw "Quadratic splines are not supported!";
            case Order.LINEAR:
                // TODO: Make me!
                // return this.init_linear_spline(cps, lw);
            default:
                throw "Order " + order + " not implemented!";
        }
    }


    init_cubic_spline(lw=2) {
        const pts = this.workingCopy;
        pts.forEach((pt, i) => {
            //const isFirst = (i == 0);
            const isLast = (i == pts.length - 1);
            if (is_knot(i, this.degree)) {
                if (!isLast) {
                    // Draw non draggable elements
                    let sel = [pts[i], pts[i+1], pts[i+2], pts[i+3]]
                    let path = this.init_path(sel, lw);
                    this.init_line(sel[0], sel[1]);
                    this.init_line(sel[2], sel[3]);
                }

                let data = filter_undefined([pts[i-1], pts[i], pts[i+1]]);
                let orig = deep_copy(data);
                let [xmin, xmax] = cubic_knot_boundaries(pts, i);
                this.make_draggable(
                    this.init_circle(pt, 3*lw, "black"),
                    delta => {
                        dst_shift(orig, delta, data);
                        this.draw_spline();
                    },
                    end => {this.init_spline() },
                    xmin,
                    xmax,
                );
            } else {
                let other = null;
                let knot = null;
                let dist = 0;
                if (i % this.degree == 1) {
                    knot = pts[i-1];
                    other = pts[i-2];
                } else {
                    knot = pts[i+1];
                    other = pts[i+2];
                }

                let [xmin, xmax] = cubic_control_point_boundaries(pts, i);
                const orig = deep_copy(pt);
                this.make_draggable(
                    this.init_circle(pt, 3*lw, "red"),
                    delta => {
                        dst_shift([orig], delta, [pt]);
                        if (other instanceof Array) {
                            designate(
                                rotate_point_mirror(pt, knot, other),
                                other
                            )
                            // TODO: Limit xmin / xmax of mirror point
                            /*
                            const [_, angle] = cartesian_to_polar(subtract_arrays(knot, pt));
                            dist = distance(knot, other);
                            designate(add_arrays(knot, polar_to_cartesian([dist, angle])), other);
                            */
                            //designate(point_mirror(pt, knot), other);
                        }
                        this.draw_spline();
                    },
                    end => {this.init_spline() },
                    xmin,
                    xmax,
                );
            }
        });
        this.draw_spline();
    }


    init_linear_spline(data, lw=2) {
        // TODO: Make me!
    }


    draw_spline() {
        for (let ele of this.svg.children) {
            ele.draw();
        }
    }


    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            const maxlen = this.duration / INTERVAL;
            this.lines.push(new Line(this.ctx, color, maxlen));
        }

        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([msg.timestamp % this.duration, value]);
        });
    }
}


customElements.define('being-editor', Editor);
