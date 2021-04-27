/**
 * @module spline_editor Spline editor custom HTML element.
 */
import {BBox} from "/static/js/bbox.js";
import {CurverBase} from "/static/js/curver.js";
import {make_draggable} from "/static/js/draggable.js";
import {History} from "/static/js/history.js";
import {clip} from "/static/js/math.js";
import {subtract_arrays, array_reshape, multiply_scalar, array_shape } from "/static/js/array.js";
import {COEFFICIENTS_DEPTH, zero_spline, BPoly} from "/static/js/spline.js";
import {clear_array} from "/static/js/utils.js";
import {Line} from "/static/js/line.js";
import {PAUSED, PLAYING, RECORDING, Transport} from "/static/js/transport.js";
import {SplineDrawer} from "/static/js/spline_drawer.js";
import {SplineList} from "/static/js/spline_list.js";
import {INTERVAL} from "/static/js/config.js";
import {DEFAULT_MOTOR_INFOS, MotorSelector} from "/static/js/motor_selector.js";
import {toggle_button, switch_button_on, switch_button_off, is_checked, enable_button, disable_button} from "/static/js/button.js";
import {Api} from "/static/js/api.js";


/** @const {number} - Magnification factor for one single click on the zoom buttons */
const ZOOM_FACTOR_PER_STEP = 1.5;

/** @const {string} - Folded motion / spline list HTML attribute */
const FOLDED = "folded";

/** @const {Number} - Default spline knot shift offset amount...  */
const DEFAULT_KNOT_SHIFT = 0.5;


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
 * Scale spline by factor (scale coefficients).
 */
function scale_spline(spline, factor) {
    const shape = array_shape(spline.c);
    const scaledCoeffs = array_reshape(multiply_scalar(factor, spline.c.flat(COEFFICIENTS_DEPTH)), shape);
    return new BPoly(scaledCoeffs, spline.x);
}


/**
 * Stretch spline by factor (stretch knots).
 */
function stretch_spline(spline, factor) {
    const stretchedKnots = multiply_scalar(factor, spline.x);
    return new BPoly(spline.c, stretchedKnots);
}


function shift_spline(spline, offset) {
    const start = spline.x[0];
    offset = Math.max(offset, -start);
    const shiftedKnots = spline.x.map(pos => {
        return pos + offset;
    });

    return new BPoly(spline.c, shiftedKnots);
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
        this._append_link("static/css/spline_editor.css");
        this.history = new History();
        this.transport = new Transport(this);
        this.drawer = new SplineDrawer(this, this.splineGroup);
        this.backgroundDrawer = new SplineDrawer(this, this.backgroundGroup);
        this.motorSelector = new MotorSelector(this);
        this.splineList = new SplineList(this);
        this.recordedTrajectory = [];
        this.api = new Api();

        this.setup_toolbar_elements();

        // Initialze data / fetch motor informations
        this.defaultBbox = new BBox([0., 0.], [1., 0.04]);
        this.api.get_motor_infos().then(infos => {
            infos.forEach(motor => {
                this.init_plotting_lines(motor.ndim);
                motor.lengths.forEach(l => {
                    this.defaultBbox.expand_by_point([1., l]);
                });
            });
            this.motorSelector.populate(infos);
        }).catch(err => {
            console.log("Failed fetching motor infos from back-end!", err);
            DEFAULT_MOTOR_INFOS.forEach(motor => {
                this.init_plotting_lines(motor.ndim);
                motor.lengths.forEach(l => {
                    this.defaultBbox.expand_by_point([1., l]);
                });
            });
            this.motorSelector.populate(DEFAULT_MOTOR_INFOS);
        });
        this.splineList.reload_spline_list();

        // TODO(atheler): Tmp workaround. Sometimes proper motor informations
        // seem to be missing. Then we do not have enough lines to plot the
        // actual motor values on. -> Assure that we have at least 2x lines for
        // the ECAL workshop.
        this.init_plotting_lines(2);

        // SVG event listeners
        this.setup_svg_drag_navigation();
        this.svg.addEventListener("click", evt => {
            this.lines.forEach(line => {
                line.data.clear();
            });
            const pt = this.mouse_coordinates(evt);
            this.transport.position = pt[0];
            this.transport.draw_cursor();
            if (this.transport.playing) {
                this.play_current_spline();
            }
        });
        this.svg.addEventListener("dblclick", evt => {
            // TODO: How to prevent accidental text selection?
            //evt.stopPropagation()
            //evt.preventDefault();
            this.stop_spline_playback();
            this.insert_new_knot(evt);
        });

        this.setup_keyboard_shortcuts();
    }

    /**
     * C1 continuity activated?
     */
    get c1() {
        return !is_checked(this.c1Btn);
    }

    /**
     * If snap to grid is enabled.
     */
    get snapping_to_grid() {
        return is_checked(this.snapBtn);
    }

    resize() {
        super.resize();
        this.draw();
    }

    /**
     * Initialize a given number of splines.
     *
     * @param {Number} maxLines Maximum number of lines.
     */
    init_plotting_lines(maxLines = 1) {
        while (this.lines.length < maxLines) {
            const color = this.colorPicker.next();
            this.lines.push(new Line(this.ctx, color, this.maxlen));
        }
    }

    /**
     * Populate toolbar with buttons and motor selection. Wire up event listeners.
     */
    setup_toolbar_elements() {
        this.listBtn = this.add_button_to_toolbar("list", "Toggle spline list");
        this.listBtn.style.display = "none";
        this.listBtn.addEventListener("click", () => {
            this.motionListDiv.toggleAttribute(FOLDED);
            this.update_ui();
            this.resize();
        });
        //this.add_space_to_toolbar();


        // Editing history buttons
        this.newBtn = this.add_button_to_toolbar("add_box", "Create new spline");
        this.newBtn.style.display = "none";
        this.newBtn.addEventListener("click", () => {
            this.create_new_spline();
        });
        this.saveBtn = this.add_button_to_toolbar("save", "Save motion");
        this.saveBtn.addEventListener("click", async () => {
            if (!this.history.length) {
                return;
            }

            const spline = this.history.retrieve();
            const name = this.splineList.selected;
            await this.api.update_spline(name, spline);
            this.history.clear();
            this.history.capture(spline);
            const selectedSpline = this.splineList.splines.filter(sp => sp.filename === this.splineList.selected)[0];
            selectedSpline.content = spline;
            this.update_ui();
        });
        this.undoBtn = this.add_button_to_toolbar("undo", "Undo last action");
        this.undoBtn.addEventListener("click", () => {
            this.undo();
        });
        this.redoBtn = this.add_button_to_toolbar("redo", "Redo last action");
        this.redoBtn.addEventListener("click", () => {
            this.redo();
        });
        this.add_space_to_toolbar();


        // Zoom buttons
        this.add_button_to_toolbar("zoom_in", "Zoom in").addEventListener("click", () => {
            zoom_bbox_in_place(this.viewport, ZOOM_FACTOR_PER_STEP);
            this.update_trafo();
            this.draw();
        });
        this.add_button_to_toolbar("zoom_out", "Zoom out").addEventListener("click", () => {
            zoom_bbox_in_place(this.viewport, 1 / ZOOM_FACTOR_PER_STEP);
            this.update_trafo();
            this.draw();
        });
        this.add_button_to_toolbar("zoom_out_map", "Reset zoom").addEventListener("click", () => {
            if (!this.history.length) return;

            const current = this.history.retrieve();
            const bbox = current.bbox();
            bbox.expand_by_bbox(this.defaultBbox);
            this.viewport = bbox;
            this.update_trafo();
            this.draw();
        });
        this.add_space_to_toolbar();


        // Motor selection
        const motorSelect = this.add_select_to_toolbar();


        // Transport buttons
        this.playPauseBtn = this.add_button_to_toolbar("play_arrow", "Play / pause motion playback");
        this.stopBtn = this.add_button_to_toolbar("stop", "Stop spline playback");
        this.stopBtn.style.display = "none";
        this.recBtn = this.add_button_to_toolbar("fiber_manual_record", "Record motion");
        this.recBtn.classList.add("record");
        this.loopBtn = this.add_button_to_toolbar("loop", "Loop spline motion");
        this.playPauseBtn.addEventListener("click", async () => {
            this.toggle_playback();
        });
        this.recBtn.addEventListener("click", () => {
            this.toggle_recording();
        });
        this.stopBtn.addEventListener("click", async () => {
            this.stop_spline_playback();
            this.transport.stop();  // Not the same as pause() which gets triggered in stop_spline_playback()!
        });
        this.loopBtn.addEventListener("click", () => {
            this.transport.toggle_looping();
            this.update_ui();
        });
        this.add_space_to_toolbar();


        // Tool adjustments
        const channelSelect = this.add_select_to_toolbar();
        this.motorSelector.attach_selects(motorSelect, channelSelect);
        this.snapBtn = this.add_button_to_toolbar("grid_3x3", "Snap to grid");  // TODO: Or vertical_align_center?
        switch_button_on(this.snapBtn);
        this.snapBtn.addEventListener("click", () => {
            toggle_button(this.snapBtn);
        });
        this.c1Btn = this.add_button_to_toolbar("timeline", "Break continous knot transitions");
        this.c1Btn.addEventListener("click", () => {
            toggle_button(this.c1Btn);
        });
        this.limitBtn = this.add_button_to_toolbar("fence", "Limit motion to selected motor");
        this.limitBtn.style.display = "none";
        switch_button_on(this.limitBtn);
        this.limitBtn.addEventListener("click", () => {
            toggle_button(this.limitBtn);
        });
        this.livePreviewBtn = this.add_button_to_toolbar("precision_manufacturing", "Toggle live preview of knot position on the motor");
        switch_button_on(this.livePreviewBtn);
        this.livePreviewBtn.addEventListener("click", () => {
            toggle_button(this.livePreviewBtn);
        });
        this.add_space_to_toolbar();


        // Spline manipulation
        this.add_button_to_toolbar("compress", "Scale down position (1/2x)").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = scale_spline(this.history.retrieve(), 0.5);
            this.spline_changed(newSpline);

        });
        this.add_button_to_toolbar("expand", "Scale up position (2x)").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = scale_spline(this.history.retrieve(), 2.0);
            this.spline_changed(newSpline);
        });
        this.add_button_to_toolbar("directions_run", "Speed up motion").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = stretch_spline(this.history.retrieve(), 0.5);
            this.spline_changed(newSpline);
        });
        this.add_button_to_toolbar("hiking", "Slow down motion").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = stretch_spline(this.history.retrieve(), 2.0);
            this.spline_changed(newSpline);
        });
        this.add_button_to_toolbar("first_page", "Move to the left. Remove delay at the beginning.").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = shift_spline(this.history.retrieve(), -Infinity);
            this.spline_changed(newSpline);
        });
        this.add_button_to_toolbar("chevron_left", "Shift knots to the left").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = shift_spline(this.history.retrieve(), -DEFAULT_KNOT_SHIFT);
            this.spline_changed(newSpline);
        });
        this.add_button_to_toolbar("chevron_right", "Shift knots to the right").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = shift_spline(this.history.retrieve(), DEFAULT_KNOT_SHIFT);
            this.spline_changed(newSpline);
        });
        this.add_space_to_toolbar()

        this.add_button_to_toolbar("clear", "Reset current motion").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const motor = this.motorSelector.selected_motor_info();
            this.spline_changed(zero_spline(motor.ndim));
        });
    }

    /**
     * Register key event listeners for shortcuts.
     */
    setup_keyboard_shortcuts() {
        addEventListener("keydown", evt => {
            if (document.activeElement !== document.body) {
                return;
            }

            const ctrlOrMeta = evt.ctrlKey || evt.metaKey;
            if (ctrlOrMeta && !evt.shiftKey) {
                switch (evt.key) {
                    case "u":
                        toggle_button(this.snapBtn);
                        break;
                    case "z":
                        this.undo();
                        break;
                }
            } else if (ctrlOrMeta && evt.shiftKey) {
                switch (evt.key) {
                    case "z":
                        this.redo();
                        break;
                }
            } else {
                switch (evt.key) {
                    case " ":
                        evt.preventDefault();
                        this.toggle_playback();
                        break;
                    case "r":
                        this.toggle_recording();
                        break;
                    case "l":
                        this.transport.toggle_looping();
                        break;
                    case "c":
                        toggle_button(this.c1Btn);
                        break;
                }
            }

            this.update_ui();
        });
    }

    /**
     * Draw spline editor stuff.
     */
    draw() {
        this.draw_lines();
        this.drawer.draw();
        this.backgroundDrawer.draw();
        this.transport.draw_cursor();
    }

    /**
     * Setup drag event handlers for moving horizontally and zooming vertically.
     */
    setup_svg_drag_navigation() {
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
                // Affine image transformation with `mid` as "focal point"
                const end = [evt.clientX, evt.clientY];
                const delta = subtract_arrays(end, start);
                const shift = -delta[0] / this.canvas.width * orig.width;
                const factor = Math.exp(-0.01 * delta[1]);
                this.viewport.left = factor * (orig.left - mid + shift) + mid;
                this.viewport.right = factor * (orig.right - mid + shift) + mid;
                this.update_trafo();
                this.draw();
            },
            () => {
                start = null;
                orig = null;
                mid = 0;
            },
        );
    }

    /**
     * Update UI elements. Mostly buttons at this time. Disabled state of undo
     * / redo buttons according to history.
     */
    update_ui() {
        if (this.motionListDiv.hasAttribute(FOLDED)) {
            switch_button_off(this.listBtn);
        } else {
            switch_button_on(this.listBtn);
        }

        this.saveBtn.disabled = !(this.history.length > 1);
        this.undoBtn.disabled = !this.history.undoable;
        this.redoBtn.disabled = !this.history.redoable;

        switch (this.transport.state) {
            case PAUSED:
                this.playPauseBtn.innerHTML = "play_arrow";
                enable_button(this.playPauseBtn);
                switch_button_off(this.playPauseBtn);

                this.recBtn.innerHTML = "fiber_manual_record";
                enable_button(this.recBtn);
                switch_button_off(this.recBtn);

                enable_button(this.stopBtn);

                this.motorSelector.disabled = false;
                break;
            case PLAYING:
                this.playPauseBtn.innerHTML = "pause";
                enable_button(this.playPauseBtn);
                switch_button_on(this.playPauseBtn);

                this.recBtn.innerHTML = "fiber_manual_record";
                disable_button(this.recBtn);
                switch_button_off(this.recBtn);

                enable_button(this.stopBtn);

                this.motorSelector.disabled = true;
                break;
            case RECORDING:
                this.playPauseBtn.innerHTML = "play_arrow";
                disable_button(this.playPauseBtn);
                switch_button_off(this.playPauseBtn);

                this.recBtn.innerHTML = "pause";
                enable_button(this.recBtn);
                switch_button_on(this.recBtn);

                disable_button(this.stopBtn);

                this.motorSelector.disabled = true;
                break;
            default:
                throw "Ooops, something went wrong with the FSM!";
        }

        if (this.transport.looping) {
            switch_button_on(this.loopBtn);
        } else {
            switch_button_off(this.loopBtn);
        }
    }

    /**
     * Get current boundaries for spline when limits activated.
     *
     * @returns {BBox} Boundaries bounding box
     */
    limits() {
        // TODO(atheler): Support for multiple and different motor lengths
        if (is_checked(this.limitBtn)) {
            const motor = this.motorSelector.selected_motor_info();
            return new BBox([0, 0], [Infinity, motor.lengths[0]]);
        } else {
            return new BBox([0, -Infinity], [Infinity, Infinity]);
        }
    }

    /**
     * Load spline into spline editor.
     * Recalculate bounding box
     */
    load_spline(spline) {
        this.history.clear();
        this.history.capture(spline);
        const bbox = spline.bbox();
        bbox.expand_by_bbox(this.defaultBbox);
        this.viewport = bbox;
        this.draw_current_spline();
    }

    /**
     * Draw current version of spline from history.
     */
    draw_current_spline() {
        const current = this.history.retrieve();

        this.viewport.ll[1] = Math.min(this.viewport.ll[1], current.min);
        this.viewport.ur[1] = Math.max(this.viewport.ur[1], current.max);
        this.update_trafo();

        const duration = current.end;
        this.transport.duration = duration;
        this.lines.forEach(line => {
            line.maxlen = .5 * .8 * duration / INTERVAL;  // Tmp workaround for the decoupling of web socket send in main loop
        });

        this.drawer.clear();
        {
            const interactive = true;
            const dim = this.motorSelector.selected_channel();
            this.drawer.draw_spline(current, interactive, dim);
        }
        this.update_ui();
    }

    /**
     * Notify spline editor that the spline working copy is going to change.
     * Also supply a optional [x, y] position value for the live preview
     * feature (if enabled).
     */
    spline_changing(position = null) {
        this.stop_spline_playback();
        this.lines.forEach(line => line.data.clear());
        if ((position !== null) && is_checked(this.livePreviewBtn)) {
            const motor = this.motorSelector.selected_motor_info();
            const channel = this.motorSelector.selected_channel();
            const [x, y] = position;
            this.transport.position = x;
            this.transport.draw_cursor();
            this.api.live_preview(y, motor.id, channel);
        }
    }

    /**
     * Notify spline editor that with the new current state of the spline.
     */
    spline_changed(workingCopy) {
        const boundaries = this.limits();
        workingCopy.restrict_to_bbox(boundaries);
        this.history.capture(workingCopy);
        this.draw_current_spline();
    }

    /**
     * Start playback of current spline in back end.
     */
    async play_current_spline() {
        const spline = this.history.retrieve();
        const motor = this.motorSelector.selected_motor_info();
        const loop = this.transport.looping;
        const offset = this.transport.position;
        const startTime = await this.api.play_spline(spline, motor.id, loop, offset);
        this.transport.startTime = startTime + INTERVAL;
        this.transport.play();
        this.update_ui();
    }

    /**
     * Stop all spline playback in back end.
     */
    async stop_spline_playback() {
        if (!this.transport.paused) {
            await this.api.stop_spline_playback();
            this.transport.pause();
            this.update_ui();
        }
    }

    /**
     * Toggle spline playback of current spline.
     */
    toggle_playback() {
        if (this.transport.playing) {
            this.stop_spline_playback();
        } else {
            this.play_current_spline();
        }
    }

    /**
     * Start recording trajectory. Disables motors in back end.
     */
    async start_recording() {
        this.transport.record();
        this.lines.forEach(line => {
            line.data.clear();
            line.data.maxlen = Infinity;
        });
        this.auto = true;
        this.drawer.clear();
        await this.api.disable_motors();
        this.update_ui();
    }

    /**
     * Stop trajectory recording, re-enable motors and fit smoothing spline
     * through trajectory via back end.
     */
    async stop_recording() {
        this.transport.stop();
        this.auto = false;
        await this.api.enable_motors();
        if (!this.recordedTrajectory.length) {
            return;
        }

        try {
            const spline = await this.api.fit_spline(this.recordedTrajectory);
            clear_array(this.recordedTrajectory);
            this.history.capture(spline);
            this.draw_current_spline();
        } catch(err) {
            console.log(err);
        }

        this.update_ui();
    }

    /**
     * Toggle trajectory recording.
     */
    toggle_recording() {
        if (this.transport.recording) {
            this.stop_recording();
        } else {
            this.start_recording();
        }
    }

    /**
     * Insert new knot into current spline.
     */
    insert_new_knot(evt) {
        if (this.history.length === 0) {
            return;
        }

        const pos = this.mouse_coordinates(evt);
        this.spline_changing(pos);
        const currentSpline = this.history.retrieve();
        const newSpline = currentSpline.copy();
        newSpline.insert_knot(pos);

        // TODO: Do some coefficients cleanup. Wrap around and maybe take the
        // direction of the previous knots as the new default coefficients...
        this.spline_changed(newSpline);
    }

    /**
     * Create a new spline.
     */
    async create_new_spline() {
        if (this.confirm_unsaved_changes()) {
            this.spline_changing();
            const motor = this.motorSelector.selected_motor_info();
            const name = await this.api.find_free_name();
            const spline = zero_spline(motor.ndim);
            await this.api.create_spline(name, spline);
            this.load_spline(spline);
            this.update_ui();
            this.splineList.selected = name;
            this.splineList.reload_spline_list();
        }
    }

    /**
     * Undo latest editing step.
     */
    undo() {
        if (this.history.undoable) {
            this.history.undo();
            this.stop_spline_playback();
            this.draw_current_spline();
        }
    }

    /**
     * Redo latest editing step.
     */
    redo() {
        if (this.history.redoable) {
            this.history.redo();
            this.stop_spline_playback();
            this.draw_current_spline();
        }
    }

    /**
     * Check if there are unsaved changes and get confirmation of the user to proceed.
     */
    confirm_unsaved_changes() {
        if (this.history.savable) {
            return confirm("Are you sure you want to leave without saving?");
        }

        return true;
    }

    /**
     * Process new data message from back-end.
     */
    new_data(msg) {
        const t = this.transport.move(msg.timestamp);
        if (this.transport.playing && t > this.transport.duration) {
            this.transport.stop();
            this.update_ui();
        }

        const motor = this.motorSelector.selected_motor_info();
        if (this.transport.paused) {
            this.lines.forEach(line => line.data.popleft());
        } else {
            motor.actualValueIndices.forEach((idx, nr) => {
                const actualValue = msg.values[idx];
                this.lines[nr].append_data([t, actualValue]);
            });
        }

        if (this.transport.recording) {
            const vals = [];
            motor.actualValueIndices.forEach(i => {
                vals.push(msg.values[i]);
            });
            this.recordedTrajectory.push([t].concat(vals));
        }
    }

    behavior_message(infos) {
        if (infos.active) {
            this.transport.stop();
            this.update_ui();
        }
    }
}


customElements.define("being-editor", Editor);
