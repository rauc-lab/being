"use strict";
/**
 * Spline editor custom HTML element.
 */
import { BBox } from "/static/js/bbox.js";
import { CurverBase } from "/static/js/curver.js";
import { make_draggable } from "/static/js/draggable.js";
import { History } from "/static/js/history.js";
import { subtract_arrays, clip } from "/static/js/math.js";
import { Order, BPoly } from "/static/js/spline.js";
import { create_element } from "/static/js/svg.js";
import { remove_all_children, fetch_json, last_element } from "/static/js/utils.js";
import { Line } from "/static/js/line.js";
import { Transport } from "/static/js/transport.js";
import { SplineDrawer } from "/static/js/spline_drawer.js";



/** Main loop interval of being block network. */
const INTERVAL = 0.010;

/** Dummy SVG point for transformations. */
const PT = create_element("svg").createSVGPoint();

/** Zero spline with duration 1.0 */
const ZERO_SPLINE = new BPoly([
    [0.],
    [0.],
    [0.],
    [0.],
], [0., 1.]);

/** Magnification factor for one single click on the zoom buttons */
const ZOOM_FACTOR_PER_STEP = 1.5;

/** Current host address */
const HOST = window.location.host;

/** Current http host address. */
const HTTP_HOST = "http://" + HOST;

/** Checked string literal */
const CHECKED = "checked";


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



/**
 * Spline editor.
 *
 * Shadow root with canvas and SVG overlay.
 */
class Editor extends CurverBase {
    constructor() {
        const auto = false;
        super(auto);
        this.history = new History();
        this.history.capture(ZERO_SPLINE);
        this.workingCopy = null;
        this.splines = []
        this.visibles = new Set()
        this.dataBbox = new BBox([0, 0], [1, 0.04]);

        this.transport = new Transport(this);

        this.drawer = new SplineDrawer(this, this.splineGroup);
        this.drawer.draw_spline(ZERO_SPLINE);

        // Editing history buttons
        this.undoBtn = this.add_button("undo", "Undo last action");
        this.undoBtn.addEventListener("click", evt => {
            this.history.undo();
            this.init_spline_elements();
            this.stop_spline_playback();
        });
        this.redoBtn = this.add_button("redo", "Redo last action")
        this.redoBtn.addEventListener("click", evt => {
            this.history.redo();
            this.init_spline_elements();
            this.stop_spline_playback();
        });

        this.add_space_to_toolbar();

        // C1 line continuity toggle button
        this.c1Btn = this.add_button("timeline", "Break continous knot transitions");
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

        // Transport buttons
        this.playPauseBtn = this.add_button("play_arrow", "Play / pause motion playback");
        this.stopBtn = this.add_button("stop", "Stop spline playback").addEventListener("click", async evt => {
            this.stop_spline_playback();
            this.transport.stop();
        });
        this.loopBtn = this.add_button("loop", "Loop spline motion");
        this.loopBtn.addEventListener("click", evt => {
            this.transport.toggle_looping();
        });
        this.playPauseBtn.addEventListener("click", async evt => {
            if (this.transport.playing) {
                this.stop_spline_playback();
            } else {
                this.play_current_spline();
            }
        });

        this.svg.addEventListener("click", evt => {
            const pt = this.mouse_coordinates(evt);
            this.transport.position = pt[0];
            this.transport.draw_cursor();
            if (this.transport.playing) {
                this.play_current_spline();
            }
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
            this.stop_spline_playback();
            this.insert_new_knot(evt);
        });
        this.setup_zoom_drag();
        this.init_spline_elements();
    }

    /**
     * C1 continuity activated?
     */
    get c1() {
        return !is_checked(this.c1Btn);
    }

    spline_changing() {
        this.stop_spline_playback();
    }

    spline_changed(workingCopy) {
        this.history.capture(workingCopy);
        this.drawer.clear();
        this.drawer.draw_spline(workingCopy);
    }

    /**
     * Update content in spline list
     */
    update_spline_list() {
        remove_all_children(this.splineListDiv)
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

                    // graph manipulation
                    this.init_spline_selection()
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
                this.init_spline_elements()
            }, true)

            this.splineListDiv.append(entry)

        })
        this.update_spline_list_selection()
        this.init_spline_elements()
    }

    init_spline_selection() {
        this.history.clear()
        const selectedSpline = this.splines.filter(sp => sp.filename === this.selected)[0]
        this.history.capture(selectedSpline.content);
        const currentSpline = this.history.retrieve();
        const bbox = currentSpline.bbox();
        bbox.expand_by_point([0., 0]);
        bbox.expand_by_point([0., .04]);
        this.dataBbox = bbox;
        this.viewport = this.dataBbox.copy();
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
            this.init_spline_selection()
        }

        this.shadowRoot.getElementById(this.selected).setAttribute("checked", "")
        this.visibles.forEach(filename => {
            const parent = this.shadowRoot.getElementById(filename)
            const checkbox = parent.querySelector(".spline-checkbox")
            checkbox.innerHTML = "visibility";
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
            throw Error(err)
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
        this.splineListDiv = document.createElement("div")
        this.splineListDiv.style.borderBottom = "2px solid black"
        this.splineListDiv.style.paddingBottom = "5px"
        container.appendChild(this.splineListDiv)
        this.addSplineButton = this.add_button("add_box", "Create new spline")
        const newBtnContainer = document.createElement("div")
        newBtnContainer.style.display = "flex"
        newBtnContainer.style.justifyContent = "center"
        newBtnContainer.appendChild(this.addSplineButton)
        container.appendChild(newBtnContainer)

        this.addSplineButton.addEventListener("click", evt => {
            this.create_spline().then(res => {
                // TODO: get latest spline from response, don't fetch again
                this.fetch_splines().then(() =>
                    this.update_spline_list()
                )
            })
        }
        )

        this.shadowRoot.insertBefore(container, this.shadowRoot.childNodes[1]) // insert after css link
    }


    /**
     * Play current spline on Being. Start transport cursor.
     */
    async play_current_spline() {
        const url = HTTP_HOST + "/api/motors/0/play";
        const spline = this.history.retrieve();
        const res = await fetch_json(url, "POST", {
            spline: spline.to_dict(),
            loop: this.transport.looping,
            offset: this.transport.position,
        });
        this.transport.startTime = res["startTime"];
        this.transport.play();
    }

    /**
     * Stop spline playback on Being.
     */
    async stop_spline_playback() {
        const url = HTTP_HOST + "/api/motors/0/stop";
        await fetch(url, { method: "POST" });
        this.transport.pause();
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
                this.drawer.draw();
                //this.draw_background_spline();
                this.transport.draw_cursor();
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
        if (this.transport.playing) {
            this.playPauseBtn.innerHTML = "pause";
        } else {
            this.playPauseBtn.innerHTML = "play_arrow";
        }

        if (this.transport.looping) {
            switch_button_on(this.loopBtn);
        } else {
            switch_button_off(this.loopBtn);
        }
    }


    /**
     * Trigger viewport resize and redraw.
     */
    resize() {
        super.resize();
        this.drawer.draw();
        //this.draw_spline();
        //this.draw_background_spline();
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
        newSpline.insert_knot(pos);

        // TODO: Do some coefficients cleanup. Wrap around and maybe take the
        // direction of the previous knots as the new default coefficients...
        this.history.capture(newSpline);
        this.drawer.clear();
        this.drawer.draw_spline(newSpline);
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

    /**
    * Create a new spline on the backend. Content is a line with 
    * arbitrary filename
    */
    async create_spline() {
        const url = HTTP_HOST + "/api/motions";
        const resp = await fetch(url, { method: "POST" });

        if (!resp.ok) {
            throw new Error(resp.statusText);
        }

        return await resp.json()
    }


    select_motor() {
        console.log("select_motor() :" + this.selMot.value);
    }


    /**
     * Set current duration of spline editor.
     */
    set_duration(duration) {
        this.transport.duration = duration;
        this.lines.forEach(line => {
            line.maxlen = .8 * (duration / INTERVAL)
        });
    }


    /**
     * Initialize spline elements.
     *
     * @param lw - Base line width.
     */
    init_spline_elements(lw = 2) {
        return;
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
        this.set_duration(last_element(currentSpline.x));
        this.update_trafo();
        //this.lines.forEach(line => line.clear());
        this.update_buttons();
        remove_all_children(this.splineGroup);
        remove_all_children(this.backgroundGroup)
        switch (currentSpline.order) {
            case Order.CUBIC:
                this.init_cubic_spline_background_elements(lw = 1); // Plot under selected!
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
        // this.draw_background_splines()
    }

    /**
    * Initialize all SVG path elements for a cubic background splines. 
    */
    init_cubic_spline_background_elements(lw = 2) {
        // TODO: To be replaced with its own spline drawer 
        return;
    }


    /**
    * Draw the current spline / update all the SVG elements. They will fetch
    * the current state from the spline via the data_source callbacks.
    */
    draw_background_spline() {
        // TODO: To be replaced with its own spline drawer 
        return;
        for (let ele of this.backgroundGroup.children) {
            if (ele.nodeName === "path")
                ele.draw();
        }
    }

    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        // Clear of old data points in live plot
        if (!this.transport.playing) {
            this.lines.forEach(line => {
                line.data.popleft();
            });
            return;
        }

        const pos = this.transport.move(msg.timestamp);

        // Init new lines
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            const maxlen = this.duration / INTERVAL;
            this.lines.push(new Line(this.ctx, color, maxlen));
        }

        // Plot data
        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([pos, value]);
        });
    }
}

customElements.define("being-editor", Editor);
