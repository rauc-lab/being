"use strict";
/**
 * Spline editor custom HTML element.
 */
import { BBox } from "/static/js/bbox.js";
import { CurverBase } from "/static/curver/curver.js";
import { make_draggable } from "/static/js/draggable.js";
import { History } from "/static/js/history.js";
import { subtract_arrays, clip } from "/static/js/math.js";
import { Degree, Order, BPoly } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import { arrays_equal, remove_all_children, assert, searchsorted, fetch_json } from "/static/js/utils.js";
import { Line } from "/static/curver/line.js";


/** Main loop interval of being block network. */
const INTERVAL = 0.010 * 1.2;  // TODO: Why do we have line overlays with the correct interval???

/** Dummy SVG point for transformations. */
const PT = create_element("svg").createSVGPoint();

/** Minimum knot distance episolon */
const EPS = 1e-3;

/** Named indices for BPoly coefficents matrix */
const KNOT = 0;
const FIRST_CP = 1;
const SECOND_CP = 2;

/** Zero spline with duration 1.0 */
const ZERO_SPLINE = new BPoly([
    [0.],
    [0.],
    [0.],
    [0.],
], [0., 1.]);


const ZOOM_FACTOR_PER_STEP = 1.5;

const HOST = window.location.host;
const HTTP_HOST = "http://" + HOST;

/** Checked string literal */
const CHECKED = "checked";

const VISIBILITY = "visibility"


/**
 * Toggle checked attribute of HTML button.
 *
 * @param {object} btn - Button to toggle.
 */
function toggle_button(btn) {
    btn.toggleAttribute(CHECKED);
}

/**
 * Switch toggle HTML button off.
 *
 * @param {object} btn - Button to switch off.
 */
function switch_button_off(btn) {
    btn.removeAttribute(CHECKED);
}


/**
 * Switch toggle HTML button on.
 *
 * @param {object} btn - Button to switch on.
 */
function switch_button_on(btn) {
    // Note: Really JS? Has it to be that way?
    if (!btn.hasAttribute(CHECKED))
        btn.toggleAttribute(CHECKED)
}


/**
 * Check if button has checked attribute / is turned on.
 *
 * @param {object} btn HTML button.
 */
function is_checked(btn) {
    return btn.hasAttribute(CHECKED);
}


/**
 * Zoom / scale bounding box in place.
 *
 * @param {Bbox} bbox Bounding box to scale.
 * @param {Number} factor Zoom factor.
 */
function zoom_bbox_in_place(bbox, factor) {
    const mid = .5 * (bbox.left + bbox.right);
    bbox.left = 1 / factor * (bbox.left - mid) + mid;
    bbox.right = 1 / factor * (bbox.right - mid) + mid;
}


function smooth_out_spline(spline) {
    const degree = spline.degree;
    for (let seg = 0; seg < spline.n_segments; seg++) {
        if (seg > 0) {
            spline.c[KNOT + degree][seg - 1] = spline.c[KNOT][seg];
        }
    }
}


/**
 * Spline mover.
 *
 * Manages spline dragging and editing. Keeps a backup copy of the original
 * spline as `orig` so that we can do delta manipulations.
 */
class Mover {
    constructor(spline) {
        assert(spline.degree == Degree.CUBIC, "Only cubic splines supported for now!");
        this.orig = spline
        this.spline = spline.copy();
    }


    /**
     * Move knot around for some delta.
     *
     * @param nr - Knot number to move.
     * @param delta - Delta 2d offset vector. Data space.
     * @param c1 - C1 continuity.
     */
    move_knot(nr, delta, c1 = true) {
        const xmin = (nr > 0) ? this.orig.x[nr - 1] + EPS : -Infinity;
        const xmax = (nr < this.orig.n_segments) ? this.orig.x[nr + 1] - EPS : Infinity;

        // Move knot horizontally
        this.spline.x[nr] = clip(this.orig.x[nr] + delta[0], xmin, xmax);
        if (nr > 0) {
            // Move knot vertically on the left
            const degree = this.spline.degree;
            this.spline.c[degree][nr - 1] = this.orig.c[degree][nr - 1] + delta[1];
        }

        if (nr < this.spline.n_segments) {
            // Move knot vertically on the right
            this.spline.c[KNOT][nr] = this.orig.c[KNOT][nr] + delta[1];
        }

        // Move control points
        if (nr == this.spline.n_segments) {
            this.move_control_point(nr - 1, SECOND_CP, delta, false);
        } else if (c1) {
            this.move_control_point(nr, FIRST_CP, delta);
        } else {
            this.move_control_point(nr, FIRST_CP, delta, false);
            this.move_control_point(nr - 1, SECOND_CP, delta, false);
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
    move_control_point(seg, nr, delta, c1 = true) {
        // Move control point vertically
        this.spline.c[nr][seg] = this.orig.c[nr][seg] + delta[1];

        // TODO: This is messy. Any better way?
        const leftMost = (seg === 0) && (nr === FIRST_CP);
        const rightMost = (seg === this.spline.n_segments - 1) && (nr === SECOND_CP);
        if (leftMost || rightMost) {
            return;
        }

        // Move adjacent control point vertically
        if (c1 && this.spline.degree == Degree.CUBIC) {
            if (nr == FIRST_CP) {
                const y = this.spline.c[KNOT][seg];
                const q = this._ratio(seg - 1);
                const dy = this.spline.c[FIRST_CP][seg] - y;
                this.spline.c[SECOND_CP][seg - 1] = y - dy / q;
            } else if (nr == SECOND_CP) {
                const y = this.spline.c[KNOT][seg + 1];
                const q = this._ratio(seg);
                const dy = this.spline.c[SECOND_CP][seg] - y;
                this.spline.c[FIRST_CP][seg + 1] = y - q * dy;
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
        this.history = new History();
        this.history.capture(ZERO_SPLINE);
        this.mover = null;
        this.splines = []
        this.visibles = new Set()
        this.dataBbox = new BBox([0, 0], [1, 0.04]);
        this.startTime = 0.;

        // Editing history buttons
        this.undoBtn = this.add_button("undo", "Undo last action");
        this.undoBtn.addEventListener("click", evt => {
            this.history.undo();
            this.init_spline_elements();
        });
        this.redoBtn = this.add_button("redo", "Redo last action")
        this.redoBtn.addEventListener("click", evt => {
            this.history.redo();
            this.init_spline_elements();
        });

        this.add_space_to_toolbar();

        // C1 line continuity toggle button
        this.c1Btn = this.add_button("timeline", "Toggle smooth knot transitions");
        switch_button_on(this.c1Btn);
        this.c1Btn.addEventListener("click", evt => {
            toggle_button(this.c1Btn);
        });

        this.add_space_to_toolbar();

        // Zoom buttons
        this.add_button("zoom_in", "Zoom In").addEventListener("click", evt => {
            zoom_bbox_in_place(this.viewport, ZOOM_FACTOR_PER_STEP);
            this.init_spline_elements();
        });
        this.add_button("zoom_out", "Zoom Out").addEventListener("click", evt => {
            zoom_bbox_in_place(this.viewport, 1 / ZOOM_FACTOR_PER_STEP);
            this.init_spline_elements();
        });
        this.add_button("zoom_out_map", "Reset zoom").addEventListener("click", evt => {
            this.viewport = this.dataBbox.copy();
            this.init_spline_elements();
        });

        this.add_space_to_toolbar();

        this.playBtn = this.add_button("play_arrow", "Play / pause motion playback");
        this.loopBtn = this.add_button("loop", "Loop spline motion");
        this.loopBtn.addEventListener("click", evt => {
            toggle_button(this.loopBtn);
        });
        this.playBtn.addEventListener("click", async evt => {
            console.log("Play");
            const url = HTTP_HOST + "/api/motors/0/play";
            const spline = this.history.retrieve();
            const res = await fetch_json(url, "POST", {
                spline: spline.to_dict(),
                loop: is_checked(this.loopBtn),
            });
            this.startTime = res['startTime'];
        });

        /*
        this.add_button("fiber_manual_record", "Record motion with motor").addEventListener("click", evt => {
            const btn = evt.target;
            if (btn.hasAttribute(CHECKED)) {
                btn.innerHTML = "fiber_manual_record";
            } else {
                btn.innerHTML = "stop";
            }
            toggle_button(btn);

        });
        this.add_button("loop", "Toogle loop motion").addEventListener("click", evt => {
            toggle_button(evt.target);
        });
        */

        /*
        const save = this.add_button("save", "Save motion", "save");
        this.isPlaying = false;
        const selMotDiv = document.createElement("div")
        selMotDiv.classList.add("btn-black")
        this.selMot = document.createElement("select");
        this.selMot.id = "select-motor"
        const label = document.createElement("label")
        label.innerHTML = "Motion Player: "
        label.for = "select-motor"
        selMotDiv.appendChild(label)
        selMotDiv.appendChild(this.selMot)
        this.toolbar.appendChild(selMotDiv);
        this.play = this.add_button("play_arrow", "Play spline on motor");
        const zoomIn = this.add_button("zoom_in", "Zoom In");
        const zoomOut = this.add_button("zoom_out", "Zoom Out");
        const zoomReset = this.add_button("zoom_out_map", "Reset Zoom");
        */

        this.add_spline_list()
        this.fetch_splines().then(() =>
            this.update_spline_list()
        )

        this.update_buttons()

        /*
        this.selMot.addEventListener("click", evt => this.select_motor())
        this.play.addEventListener("click", evt => this.play_motion(this.play))
        save.addEventListener("click", evt => this.save_spline(save))
        */
        this.svg.addEventListener("dblclick", evt => {
            // TODO: How to prevent accidental text selection?
            //evt.stopPropagation()
            //evt.preventDefault();
            this.insert_new_knot(evt);
        });
        this.setup_zoom_drag();
        this.init_spline_elements();
    }

    /**
     * Update content in spline list
     */
    update_spline_list() {
        this.splines.forEach(spline => {
            const entry = document.createElement("div")
            entry.classList.add("spline-list-entry")
            entry.id = spline.filename
            const checkbox = document.createElement("span")
            checkbox.classList.add("spline-checkbox")
            checkbox.classList.add("material-icons")
            checkbox.classList.add("mdc-icon-button")
            checkbox.innerHTML = ""
            checkbox.value = spline.filename
            checkbox.title = "Show in Graph"
            const text = document.createElement("span")
            text.innerHTML = spline.filename
            entry.append(checkbox, text)

            entry.addEventListener("click", evt => {
                if (evt.currentTarget.id !== this.selected) {
                    // Cant unselect current spline, at least one spline needs 
                    // to be selected. Also we want the current selected spline 
                    // to be visible in the graph.
                    this.selected = evt.currentTarget.id
                    this.visibles.add(evt.currentTarget.id)
                    this.update_spline_list_selection()
                    this.history.clear()
                    const selectedSpline = this.splines.filter(sp => sp.filename === this.selected)[0]
                    this.history.capture(selectedSpline.content);
                    const currentSpline = this.history.retrieve();
                    const bbox = currentSpline.bbox();
                    bbox.expand_by_point([0., 0]);
                    bbox.expand_by_point([0., .04]);
                    this.dataBbox = bbox;
                    this.viewport = this.dataBbox.copy();
                    this.init_spline_elements()
                }
            })

            checkbox.addEventListener("click", evt => {
                evt.stopPropagation()
                const filename = evt.target.parentNode.id
                if (this.selected !== filename) {
                    if (this.visibles.has(filename)) {
                        this.visibles.delete(filename)
                    }
                    else {
                        this.visibles.add(filename)
                    }
                }
                this.update_spline_list_selection()
            }, true)

            this.spline_list_div.append(entry)

        })
        this.update_spline_list_selection()
    }

    update_spline_list_selection() {

        let entries = this.shadowRoot.querySelectorAll(".spline-list-entry")
        entries.forEach(entry => {
            entry.removeAttribute("checked")
            entry.querySelector(".spline-checkbox").innerHTML = ""
        })

        // Preselection 
        if (this.selected == null) {
            const latest = this.splines.length - 1
            if (latest >= 0) {
                const spline_fd = this.splines[latest].filename
                this.selected = spline_fd
                this.visibles.add(spline_fd)
            }
        }

        this.shadowRoot.getElementById(this.selected).setAttribute("checked", "")
        this.visibles.forEach(filename => {
            const parent = this.shadowRoot.getElementById(filename)
            const checkbox = parent.querySelector(".spline-checkbox")
            checkbox.innerHTML = VISIBILITY
        })
    }

    /**
     * Get splines from API
     */
    async fetch_splines() {
        try {
            return await fetch_json("/api/motions").then(res => {
                this.splines = res
                this.splines.forEach(spline => {
                    spline.content = BPoly.from_object(spline.content)
                })
            })
        }
        catch (err) {
            throw Error(error)
        }
    }

    /**
     * Spline list selection
     */
    add_spline_list() {
        const container = document.createElement("div")
        container.classList.add("spline-list")
        const title = document.createElement("h2")
        title.appendChild(document.createTextNode("Motions"))
        container.appendChild(title)
        this.spline_list_div = document.createElement("div")
        container.appendChild(this.spline_list_div)
        this.shadowRoot.insertBefore(container, this.shadowRoot.childNodes[1]) // insert after css link
    }


    /**
     * C1 continuity activated?
     */
    get c1() {
        return is_checked(this.c1Btn);
    }


    /**
     * Setup drag event handlers for moving horizontally and zooming vertically.
     */
    setup_zoom_drag() {
        let start = null;
        let orig = null;
        let mid = 0;

        make_draggable(
            this.svg,
            evt => {
                start = [evt.clientX, evt.clientY];
                orig = this.viewport.copy();
                const pt = this.mouse_coordinates(evt);
                const alpha = clip((pt[0] - orig.left) / orig.width, 0, 1);
                mid = orig.left + alpha * orig.width;
            },
            evt => {
                const end = [evt.clientX, evt.clientY];
                const delta = subtract_arrays(end, start);
                const shift = -delta[0] / this.width * orig.width;
                const factor = Math.exp(-0.01 * delta[1]);
                this.viewport.left = factor * (orig.left - mid + shift) + mid;
                this.viewport.right = factor * (orig.right - mid + shift) + mid;
                this.update_trafo();
                this.draw_spline();
            },
            evt => {
                start = null;
                orig = null;
                mid = 0;
            },
        );
    }


    /**
     * Update disabled state of undo / redo buttons according to history.
     */
    update_buttons() {
        this.undoBtn.disabled = !this.history.undoable;
        this.redoBtn.disabled = !this.history.redoable;
    }


    /**
     * Trigger viewport resize and redraw.
     */
    resize() {
        super.resize();
        this.draw_spline();
    }


    /**
     * Coordinates of mouse event inside canvas / SVG data space.
     * 
     * @param {MouseEvent} evt Mouse event to transform into data space.
     */
    mouse_coordinates(evt) {
        PT.x = evt.clientX;
        PT.y = evt.clientY;
        let a = PT.matrixTransform(this.ctmInv);
        let b = (new DOMPoint(a.x, a.y)).matrixTransform(this.trafoInv);
        return [b.x, b.y];
    }


    /**
     * Make something draggable inside data space. Wraps default
     * make_draggable. Handles mouse -> image space -> data space
     * transformation, calculates delta offset, triggers redraws. Mostly used
     * to drag SVG elements around.
     *
     * @param ele - Element to make draggable.
     * @param on_drag - On drag motion callback. Will be called with a relative
     * delta array.
     */
    make_draggable(ele, on_drag) {
        /** Start position of drag motion. */
        let start = null;

        make_draggable(
            ele,
            evt => {
                start = this.mouse_coordinates(evt);
                console.log("Mouse down. TODO: Pause behavior engine")
            },
            evt => {
                const end = this.mouse_coordinates(evt);
                const delta = subtract_arrays(end, start);
                on_drag(delta);
                this.draw_spline();
            },
            evt => {
                const end = this.mouse_coordinates(evt);
                if (arrays_equal(start, end)) {
                    return;
                }

                this.history.capture(this.mover.spline);
                this.init_spline_elements();
            },
        )
    }


    /**
     * Insert new knot into current spline.
     */
    insert_new_knot(evt) {
        if (this.history.length === 0) {
            return;
        }

        const pos = this.mouse_coordinates(evt);
        const currentSpline = this.history.retrieve();
        const newSpline = currentSpline.copy();
        const index = searchsorted(newSpline.x, pos[0]);
        newSpline.x.splice(index, 0, pos[0]);
        newSpline.c.forEach(row => {
            row.splice(index, 0, pos[1]);
        });

        smooth_out_spline(newSpline);

        // TODO: Do some coefficients cleanup. Wrap around and maybe take the
        // direction of the previous knots as the new default coefficients...
        this.history.capture(newSpline);
        this.init_spline_elements();
    }



    /**
     * Load spline into spline editor.
     */
    load_spline(spline) {
        this.history.clear();
        this.history.capture(spline);
        this.init_spline_elements();
    }

    save_spline() {
        console.log("save_spline()");
    }


    select_motor() {
        console.log("select_motor() :" + this.selMot.value);
    }

    /**
     * Play back spline on motors
     *
     * @param {*} el 
     */
    play_motion(el) {
        this.isPlaying = !this.isPlaying
        if (this.isPlaying) {
            // TODO: Call API
            el.innerHTML = "stop"
            el.style.color = "red"
            el.title = "Stop playback"

        }
        else {
            el.title = "Play spline on motor"
            el.style.color = "black"
            el.innerHTML = "play_circle"
        }
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
     *
     * @param lw - Base line width.
     */
    init_spline_elements(lw = 2) {
        if (this.history.length === 0) {
            return;
        }


        const currentSpline = this.history.retrieve();
        const bbox = currentSpline.bbox();
        bbox.expand_by_point([0., 0]);
        bbox.expand_by_point([0., .04]);
        this.dataBbox = bbox;
        this.viewport.ll[1] = bbox.ll[1];
        this.viewport.ur[1] = bbox.ur[1];
        this.set_duration(currentSpline.duration);
        this.update_trafo();
        //this.lines.forEach(line => line.clear());
        this.update_buttons();
        remove_all_children(this.svg);
        switch (currentSpline.order) {
            case Order.CUBIC:
                this.init_cubic_spline_elements(lw);
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
    init_path(data_source, strokeWidth = 1, color = "black") {
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
    init_circle(data_source, radius = 1, color = "black") {
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
    init_line(data_source, strokeWidth = 1, color = "black") {
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
     * callbacks. We create a copy of the current spline (working copy) on
     * which the drag handlers will be placed.
     */
    init_cubic_spline_elements(lw = 2) {
        const currentSpline = this.history.retrieve();
        this.mover = new Mover(currentSpline);
        const spline = this.mover.spline;  // Working copy
        //console.table(spline.c);
        for (let seg = 0; seg < spline.n_segments; seg++) {
            this.init_path(() => {
                return [
                    spline.point(seg, 0),
                    spline.point(seg, 1),
                    spline.point(seg, 2),
                    spline.point(seg + 1, 0),
                ];
            }, lw);
            this.init_line(() => {
                return [spline.point(seg, 0), spline.point(seg, 1)];
            });
            this.init_line(() => {
                return [spline.point(seg, 2), spline.point(seg + 1, 0)];
            });

            for (let cpNr = 1; cpNr < spline.degree; cpNr++) {
                this.make_draggable(
                    this.init_circle(() => {
                        return spline.point(seg, cpNr);
                    }, 3 * lw, "red"),
                    (delta) => {
                        this.mover.move_control_point(seg, cpNr, delta, this.c1);
                    },
                );
            }
        }

        for (let knotNr = 0; knotNr <= spline.n_segments; knotNr++) {
            const circle = this.init_circle(() => {
                return spline.point(knotNr);
            }, 3 * lw);
            this.make_draggable(
                circle,
                (delta) => {
                    this.mover.move_knot(knotNr, delta, this.c1);
                },
            );
            circle.addEventListener("dblclick", evt => {
                evt.stopPropagation();
                const currentSpline = this.history.retrieve();
                const newSpline = currentSpline.copy();
                const index = clip(knotNr, 0, currentSpline.n_segments);
                newSpline.x.splice(index, 1);
                newSpline.c.forEach(row => {
                    row.splice(index, 1);
                })
                this.history.capture(newSpline);
                this.init_spline_elements();
            });
        }

        this.draw_spline()
    }


    init_linear_spline(data, lw = 2) {
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
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            const maxlen = this.duration / INTERVAL;
            this.lines.push(new Line(this.ctx, color, maxlen));
        }

        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([
                (msg.timestamp - this.startTime) % this.duration,
                value,
            ]);
        });
    }
}


customElements.define('being-editor', Editor);
