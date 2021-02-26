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
    assert,
} from "/static/js/utils.js";
import {Deque} from "/static/js/deque.js";
import {
    MS,
    TAU,
    PI,
} from "/static/js/constants.js";
import {
    Degree,
    Order,
    spline_order,
    spline_degree,
} from "/static/js/spline.js";


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



const EPS = .1;
const KNOT = 0;
const FIRST_CP = 1;
const SECOND_CP = 2;


/**
 * Spline mover.
 *
 * Manages spline dragging and editing. Keeps a backup copy of the original
 * spline as `orig` so that we can do delta manipulations.
 */
class Mover {
    constructor(spline) {
        assert(spline.degree == Degree.CUBIC, "Only cubic splines supported for now!");
        this.spline = spline;
        this.x = spline.x;
        this.c = spline.c;
        this.degree = spline.degree;
        this.orig = spline.copy();
    }


    /**
     * Move knot around for some delta.
     */
    move_knot(nr, delta, c1=true) {
        const xmin = (nr > 0) ? this.orig.x[nr-1] + EPS : -Infinity;
        const xmax = (nr < this.orig.n_segments) ? this.orig.x[nr+1] - EPS : Infinity;

        // Move knot horizontally
        this.x[nr] = clip(this.orig.x[nr] + delta[0], xmin, xmax);
        if (nr > 0) {
            // Move knot vertically on the left
            this.c[this.degree][nr-1] = this.orig.c[this.degree][nr-1] + delta[1];
        }

        if (nr < this.spline.n_segments) {
            // Move knot vertically on the right
            this.c[KNOT][nr] = this.orig.c[KNOT][nr] + delta[1];
        }

        // Move control points
        if (nr == this.spline.n_segments) {
            this.move_control_point(nr-1, SECOND_CP, delta, false);
        } else if (c1) {
            this.move_control_point(nr, FIRST_CP, delta);
        } else {
            this.move_control_point(nr, FIRST_CP, delta, false);
            this.move_control_point(nr-1, SECOND_CP, delta, false);
        }
    }


    /**
     * X axis spacing ratio between two consecutive segments
     */
    _ratio(seg) {
        return this.spline._dx(seg + 1) / this.spline._dx(seg);
    }


    /**
     * Move control point around by some delta.
     */
    move_control_point(seg, nr, delta, c1=true) {
        // Move control point vertically
        this.c[nr][seg] = this.orig.c[nr][seg] + delta[1];

        // TODO: This is messy. Any better way?
        const leftMost = (seg === 0) && (nr === FIRST_CP);
        const rightMost = (seg === this.spline.n_segments - 1) && (nr === SECOND_CP);
        if (leftMost || rightMost) {
            return;
        }

        // Move adjacent control point vertically
        if (c1 && this.degree == Degree.CUBIC) {
            if (nr == FIRST_CP) {
                const y = this.c[KNOT][seg];
                const q = this._ratio(seg-1);
                const dy = this.c[FIRST_CP][seg] - y;
                this.c[SECOND_CP][seg-1] = y - dy / q;
            } else if (nr == SECOND_CP) {
                const y = this.c[KNOT][seg+1];
                const q = this._ratio(seg);
                const dy = this.c[SECOND_CP][seg] - y;
                this.c[FIRST_CP][seg+1] = y - q * dy;
            }
        }
    }
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
        this.duration = 1;
        this.maxlen = 1;
    }


    /**
     * Trigger viewport resize and redraw.
     */
    resize() {
        super.resize();
        this.draw_spline();
    }


    /**
     * Transform a data point -> view space.
     */
    transform_point(pt) {
        const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
        return [ptHat.x, ptHat.y];
    }


    /**
     * Transform multiple data point into view space.
     */
    transform_points(pts) {
        return pts.map(pt => {
            const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
            return [ptHat.x, ptHat.y];
        });
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


    /**
     * Make element draggable. Handles mouse -> image space -> data space
     * transformation, calculates delta offset, triggers redraws.
     */
    make_draggable(ele, on_drag) {
        /** Start position of drag motion. */
        let start = null;


        function enable_drag_listeners() {
            addEventListener("mousemove", drag);
            addEventListener("mouseup", end_drag);
            addEventListener("mouseleave", end_drag);
            addEventListener("keyup", escape_drag);
        }


        function disable_drag_listeners() {
            removeEventListener("mousemove", drag);
            removeEventListener("mouseup", end_drag);
            removeEventListener("mouseleave", end_drag);
            removeEventListener("keyup", escape_drag);
        }


        /**
         * Start drag movement.
         */
        const start_drag = evt => {
            disable_drag_listeners();  // TODO: Do we need this?
            enable_drag_listeners();
            start = this.mouse_coordinates(evt);
        };

        ele.addEventListener("mousedown", start_drag);


        /**
         * Drag element.
         */
        const drag = evt => {
            const end = this.mouse_coordinates(evt);
            const delta = subtract_arrays(end, start);
            on_drag(delta);
            this.draw_spline();
        }


        /**
         * Escape drag by hitting escape.
         */
        function escape_drag(evt) {
            const escKeyCode = 27;
            if (evt.keyCode == escKeyCode) {
                end_drag();
            }
        }


        /**
         * End dragging of element.
         */
        const end_drag = evt => {
            disable_drag_listeners();
            const end = this.mouse_coordinates(evt);
            if (!arrays_equal(start, end)) {
                this.init_spline();
            }
        }
    }


    /**
     * Load spline into spline editor.
     */
    load_spline(spline) {
        this.spline = spline;
        this.init_spline();
    }


    /**
     * Set current duration of spline editor.
     */
    set_duration(duration) {
        this.duration = duration;
        this.lines.forEach(line => {
            line.maxlen = this.duration / INTERVAL
        });
    }


    /**
     * Initialize spline elements.
     * @param cps - Control point tensor.
     */
    init_spline(lw=2) {
        console.log("init_spline()");
        this.set_duration(this.spline.duration);
        this.bbox = this.spline.bbox();
        this.update_trafo();
        this.lines.forEach(line => line.clear());
        remove_all_children(this.svg);
        switch (this.spline.order) {
            case Order.CUBIC:
                this.init_cubic_spline(lw);
                break;
            case Order.QUADRATIC:
                throw "Quadratic splines are not supported!";
            case Order.LINEAR:
                // TODO: Make me!
                // return this.init_linear_spline(cps, lw);
            default:
                throw "Order " + order + " not implemented!";
        }

        this.draw_spline();
    }


    /**
     * Initialize an SVG path element and adds it to the SVG parent element.
     * data_source callback needs to deliver the 2-4 Bézier control points.
     */
    init_path(data_source, strokeWidth=1, color="black") {
        const path = create_element('path');
        setattr(path, "stroke", color);
        setattr(path, "stroke-width", strokeWidth);
        setattr(path, "fill", "transparent");
        this.svg.appendChild(path)
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(data_source())));
        };

        return path
    }


    /**
     * Initialize an SVG circle element and adds it to the SVG parent element.
     * data_source callback needs to deliver the center point of the circle.
     */
    init_circle(data_source, radius=1, color="black") {
        const circle = create_element('circle');
        setattr(circle, "r", radius);
        setattr(circle, "fill", color);
        this.svg.appendChild(circle);
        circle.draw = () => {
            const a = this.transform_point(data_source());
            setattr(circle, "cx", a[0]);
            setattr(circle, "cy", a[1]);
        };

        return circle;
    }
   

    /**
     * Initialize an SVG line element and adds it to the SVG parent element.
     * data_source callback needs to deliver the start end and point of the
     * line.
     */
    init_line(data_source, strokeWidth=1, color="black") {
        const line = create_element("line");
        setattr(line, "stroke-width", strokeWidth);
        setattr(line, "stroke", color);
        this.svg.appendChild(line);
        line.draw = () => {
            const [start, end] = data_source();
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
     * Initialize all SVG elements for a cubic spline. Hooks up the draggable
     * callbacks.
     */
    init_cubic_spline(lw=2) {
        const spline = this.spline;
        const mover = new Mover(spline);
        for (let seg=0; seg<spline.n_segments; seg++) {
            this.init_path(() => {
                return [
                    spline.point(seg, 0),
                    spline.point(seg, 1),
                    spline.point(seg, 2),
                    spline.point(seg+1, 0),
                ]
            }, lw);
            this.init_line(() => {
                return [spline.point(seg, 0), spline.point(seg, 1)];
            });
            this.init_line(() => {
                return [spline.point(seg, 2), spline.point(seg+1, 0)];
            });

            for (let nr=1; nr<spline.degree; nr++) {
                this.make_draggable(
                    this.init_circle(() => {
                        return spline.point(seg, nr);
                    }, 3*lw, "red"),
                    (delta) => {
                        mover.move_control_point(seg, nr, delta);
                    },
                );
            }
        }

        for (let knotNr=0; knotNr<=spline.n_segments; knotNr++) {
            this.make_draggable(
                this.init_circle(() => {
                    return spline.point(knotNr);
                }, 3*lw),
                (delta) => {
                    mover.move_knot(knotNr, delta);
                },
            );
        }
        this.draw_spline()
    }


    init_linear_spline(data, lw=2) {
        // TODO: Make me!
    }


    /**
     * Draw the current spline / update all the SVG elements. They will fetch
     * the current state from the spline via the data_source callbacks.
     */
    draw_spline() {
        for (let ele of this.svg.children) {
            ele.draw();
        }
    }


    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        return;
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
