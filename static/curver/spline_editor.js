"use strict";
/**
 * Spline editor custom HTML element.
 */
import { History, } from "/static/js/history.js";
import {
    subtract_arrays,
    clip,
} from "/static/js/math.js";
import {
    create_element,
    path_d,
    setattr,
} from "/static/js/svg.js";
import {
    arrays_equal,
    remove_all_children,
    assert,
} from "/static/js/utils.js";
import {
    Degree,
    Order,
} from "/static/js/spline.js";
import {CurverBase} from "/static/curver/curver.js";


/** Main loop interval of being block network. */
const INTERVAL = 0.010 * 1.2;  // TODO: Why do we have line overlays with the correct interval???

/** Dummy SVG point for transformations. */
const PT = create_element("svg").createSVGPoint();

/** Minimum knot distance episolon */
const EPS = .1;

/** Named indices for BPoly coefficents matrix */
const KNOT = 0;
const FIRST_CP = 1;
const SECOND_CP = 2;
const LEFT_MOUSE_BUTTON = 1;


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

        var self = this;
        //this.history = new History();
        const save = document.createElement("button");
        save.classList.add("btn-black")
        save.classList.add("mdc-icon-button")
        save.classList.add("material-icons")
        save.id = "btn-save"
        save.innerHTML = "save";
        save.title = "Save spline"
        save.addEventListener("click", e => self.save_spline(save))
        this.toolbar.appendChild(save);

        const selMot = document.createElement("button");
        selMot.classList.add("btn-black")
        selMot.id = "btn-save"
        selMot.innerHTML = "Select Motor";
        selMot.addEventListener("click", e => self.select_motor(selMot))
        this.toolbar.appendChild(selMot);

        // TODO : Toggle button start / stop
        const play = document.createElement("button")
        play.classList.add("btn-black")
        play.classList.add("mdc-icon-button")
        play.classList.add("material-icons")
        play.title = "Play spline on motor"
        play.innerHTML = "play_circle"
        this.toolbar.appendChild(play)

        const stop = document.createElement("button")
        stop.classList.add("btn-black")
        stop.classList.add("mdc-icon-button")
        stop.classList.add("material-icons")
        stop.title = "Stop playback"
        stop.innerHTML = "stop"
        // div_behavior.appendChild(stop)
        this.toolbar.appendChild(stop)

        const zoomIn = document.createElement("button")
        zoomIn.classList.add("btn-black")
        zoomIn.classList.add("mdc-icon-button")
        zoomIn.classList.add("material-icons")
        zoomIn.innerHTML = "zoom_in"
        zoomIn.title = "Zoom in "
        this.toolbar.appendChild(zoomIn);

        const zoomOut = document.createElement("button")
        zoomOut.classList.add("btn-black")
        zoomOut.classList.add("mdc-icon-button")
        zoomOut.classList.add("material-icons")
        zoomOut.innerHTML = "zoom_out"
        zoomOut.title = "Zoom out"
        this.toolbar.appendChild(zoomOut);

        const zoomReset = document.createElement("button")
        zoomReset.classList.add("btn-black")
        zoomReset.classList.add("mdc-icon-button")
        zoomReset.classList.add("material-icons")
        zoomReset.innerHTML = "zoom_out_map"
        zoomReset.title = "Reset zoom"
        this.toolbar.appendChild(zoomReset);

        const undo = document.createElement("button")
        undo.classList.add("btn-black")
        undo.classList.add("mdc-icon-button")
        undo.classList.add("material-icons")
        undo.innerHTML = "undo"
        undo.title = "Undo"
        this.toolbar.appendChild(undo);

        const redo = document.createElement("button")
        redo.classList.add("btn-black")
        redo.classList.add("mdc-icon-button")
        redo.classList.add("material-icons")
        redo.innerHTML = "redo"
        redo.title = "Redo"
        this.toolbar.appendChild(redo);
    }


    save_spline(el) {}

    select_motor(el) {}


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


        /**
         * Enable all event listeners for drag action. 
         */
        function enable_drag_listeners() {
            addEventListener("mousemove", drag);
            addEventListener("mouseup", end_drag);
            addEventListener("mouseleave", end_drag);
            addEventListener("keyup", escape_drag);
        }


        /**
         * Disable all event listerns of drag action.
         */
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
            if (evt.which !== LEFT_MOUSE_BUTTON) {
                return;
            }

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
         * Escape drag by hitting escape key.
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
     * @param lw - Base line width.
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
                ];
            }, lw);
            this.init_line(() => {
                return [spline.point(seg, 0), spline.point(seg, 1)];
            });
            this.init_line(() => {
                return [spline.point(seg, 2), spline.point(seg + 1, 0)];
            });

            for (let cpNr=1; cpNr<spline.degree; cpNr++) {
                this.make_draggable(
                    this.init_circle(() => {
                        return spline.point(seg, cpNr);
                    }, 3*lw, "red"),
                    (delta) => {
                        mover.move_control_point(seg, cpNr, delta);
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
