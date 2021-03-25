"use strict";
/**
 * Spline editor custom HTML element.
 */
import { BBox } from "/static/js/bbox.js";
import { CurverBase } from "/static/js/curver.js";
import { make_draggable } from "/static/js/draggable.js";
import { History } from "/static/js/history.js";
import { subtract_arrays, clip, array_reshape, multiply_scalar, array_shape } from "/static/js/math.js";
import { BPoly } from "/static/js/spline.js";
import { clear_array } from "/static/js/utils.js";
import { Line } from "/static/js/line.js";
import { PAUSED, PLAYING, RECORDING, Transport } from "/static/js/transport.js";
import { SplineDrawer } from "/static/js/spline_drawer.js";
import { SplineList } from "/static/js/spline_list.js";
import { INTERVAL } from "/static/js/config.js";
import { MotorSelector } from "/static/js/motor_selector.js";
import { toggle_button, switch_button_on, switch_button_off, is_checked, enable_button, disable_button } from "/static/js/button.js";
import { Api } from "/static/js/api.js";


/** Zero spline with duration 1.0 */
const ZERO_SPLINE = new BPoly([
    [0.],
    [0.],
    [0.],
    [0.],
], [0., 1.]);

/** Magnification factor for one single click on the zoom buttons */
const ZOOM_FACTOR_PER_STEP = 1.5;

/** Default data bbox size. */
const DEFAULT_DATA_BBOX = new BBox([0, 0], [1, 0.04]);


const MIN_HEIGHT = 0.010;


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
    const scaledC = array_reshape(multiply_scalar(factor, spline.c.flat()), shape);
    return new BPoly(scaledC, spline.x);
}


/**
 * Stretch spline by factor (scale knots).
 */
function stretch_spline(spline, factor) {
    const newX = multiply_scalar(factor, spline.x);
    return new BPoly(spline.c, newX);
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
        this.transport = new Transport(this);
        this.drawer = new SplineDrawer(this, this.splineGroup);
        this.backgroundDrawer = new SplineDrawer(this, this.backgroundGroup);
        this.motorSelector = null;  // Gets initialized inside setup_toolbar_elements(). Not nice but...
        this.splineList = new SplineList(this);
        this.recordedTrajectory = [];
        this.api = new Api();

        // Single actual value line
        const color = this.colorPicker.next();
        this.line = new Line(this.ctx, color, this.maxlen);
        this.lines.push(this.line);

        this.setup_toolbar_elements();

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

        // Initial data
        this.api.get_motor_infos().then(infos => {
            this.motorSelector.populate(infos);
        });

        this.splineList.reload_spline_list()
    }

    /**
     * C1 continuity activated?
     */
    get c1() {
        return !is_checked(this.c1Btn);
    }

    /**
     * Populate toolbar with buttons and motor selection. Wire up event listeners.
     */
    setup_toolbar_elements() {
        // Motor selection
        const select = this.add_select();
        select.addEventListener("change", evt => {
            this.stop_spline_playback();
        });
        this.motorSelector = new MotorSelector(select);

        // Transport buttons
        this.playPauseBtn = this.add_button("play_arrow", "Play / pause motion playback");
        this.recBtn = this.add_button("fiber_manual_record", "Record motion");
        this.recBtn.classList.add("record");
        this.stopBtn = this.add_button("stop", "Stop spline playback");
        this.loopBtn = this.add_button("loop", "Loop spline motion");
        this.playPauseBtn.addEventListener("click", async evt => {
            if (this.transport.playing) {
                this.stop_spline_playback();
            } else {
                this.play_current_spline();
            }
        });
        this.recBtn.addEventListener("click", evt => {
            if (this.transport.recording) {
                this.stop_recording();
            } else {
                this.start_recording();
            }
            this.update_ui();
        });
        this.stopBtn.addEventListener("click", async evt => {
            this.stop_spline_playback();
            this.transport.stop();  // Not the same as pause() which gets triggered in stop_spline_playback()!
        });
        this.loopBtn.addEventListener("click", evt => {
            this.transport.toggle_looping();
            this.update_ui();
        });

        this.add_space_to_toolbar();

        // Tool adjustments
        this.livePreviewBtn = this.add_button("precision_manufacturing", "Toggle live preview of knot position on the motor");
        switch_button_on(this.livePreviewBtn);
        this.livePreviewBtn.addEventListener("click", evt => {
            toggle_button(this.livePreviewBtn);
        });
        this.c1Btn = this.add_button("timeline", "Break continous knot transitions");
        this.c1Btn.addEventListener("click", evt => {
            toggle_button(this.c1Btn);
        });

        this.add_space_to_toolbar();

        // Zoom buttons
        this.add_button("zoom_in", "Zoom In").addEventListener("click", evt => {
            zoom_bbox_in_place(this.viewport, ZOOM_FACTOR_PER_STEP);
            this.update_trafo();
            this.draw();
        });
        this.add_button("zoom_out", "Zoom Out").addEventListener("click", evt => {
            zoom_bbox_in_place(this.viewport, 1 / ZOOM_FACTOR_PER_STEP);
            this.update_trafo();
            this.draw();
        });
        this.add_button("zoom_out_map", "Reset zoom").addEventListener("click", evt => {
            if (!this.history.length) return;

            const current = this.history.retrieve();
            const bbox = current.bbox();
            bbox.expand_by_bbox(DEFAULT_DATA_BBOX);
            this.viewport = current.bbox();
            this.update_trafo();
            this.draw();
        });

        this.add_space_to_toolbar();

        // Editing history buttons
        this.undoBtn = this.add_button("undo", "Undo last action");
        this.undoBtn.addEventListener("click", evt => {
            this.history.undo();
            this.stop_spline_playback();
            this.draw_current_spline();
        });
        this.redoBtn = this.add_button("redo", "Redo last action")
        this.redoBtn.addEventListener("click", evt => {
            this.history.redo();
            this.stop_spline_playback();
            this.draw_current_spline();
        });
        this.add_button("save", "Save motion").addEventListener("click", async evt => {
            if (!this.history.length) {
                return;
            }

            const spline = this.history.retrieve();
            const name = this.splineList.selected;
            await this.api.save_spline(spline, name);
            this.history.clear();
            this.history.capture(spline);
            this.history.isUnsaved = false;
            const selectedSpline = this.splineList.splines.filter(sp => sp.filename === this.splineList.selected)[0]
            selectedSpline.content = spline;
            this.update_ui();
        })

        this.add_space_to_toolbar();

        // Scaling and stretching spline
        this.add_button("compress", "Half motion height").addEventListener("click", evt => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = scale_spline(this.history.retrieve(), 0.5);
            this.spline_changed(newSpline);

        });
        this.add_button("expand", "Double motion height").addEventListener("click", evt => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = scale_spline(this.history.retrieve(), 2.0);
            this.spline_changed(newSpline);
        });

        this.add_space_to_toolbar();

        this.add_button("directions_run", "Speed up motion").addEventListener("click", evt => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = stretch_spline(this.history.retrieve(), 0.5);
            this.spline_changed(newSpline);
        });
        this.add_button("hiking", "Slow down motion").addEventListener("click", evt => {
            if (!this.history.length) {
                return;
            }

            this.spline_changing();
            const newSpline = stretch_spline(this.history.retrieve(), 2.0);
            this.spline_changed(newSpline);
        });
    }


    /**
     * Trigger viewport resize and redraw.
     */
    resize() {
        super.resize();
        this.draw();
    }


    /**
     * Draw spline editor stuff.
     */
    draw() {
        this.drawer.draw();
        this.backgroundDrawer.draw()
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
                const shift = -delta[0] / this.width * orig.width;
                const factor = Math.exp(-0.01 * delta[1]);
                this.viewport.left = factor * (orig.left - mid + shift) + mid;
                this.viewport.right = factor * (orig.right - mid + shift) + mid;
                this.update_trafo();
                this.draw();
            },
            evt => {
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
                break;
            case PLAYING:
                this.playPauseBtn.innerHTML = "pause";
                enable_button(this.playPauseBtn);
                switch_button_on(this.playPauseBtn);

                this.recBtn.innerHTML = "fiber_manual_record";
                disable_button(this.recBtn);
                switch_button_off(this.recBtn);

                enable_button(this.stopBtn);
                break;
            case RECORDING:
                this.playPauseBtn.innerHTML = "play_arrow";
                disable_button(this.playPauseBtn);
                switch_button_off(this.playPauseBtn);

                this.recBtn.innerHTML = "pause";
                enable_button(this.recBtn);
                switch_button_on(this.recBtn);

                disable_button(this.stopBtn);
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
     * Load spline into spline editor.
     * Recalculate bounding box
     */
    load_spline(spline) {
        this.history.clear();
        this.history.capture(spline);
        this.history.isUnsaved = false;

        // Calc viewport
        const bbox = spline.bbox();
        if (bbox.height === 0) {
            bbox.ll[1] -= .5 * MIN_HEIGHT;
            bbox.ur[1] += .5 * MIN_HEIGHT;
        }
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

        this.transport.duration = current.duration;
        this.line.maxlen = .8 * current.duration / INTERVAL;

        this.drawer.clear();
        this.drawer.draw_spline(current);

        this.update_ui();
    }


    /**
     * Notify spline editor that the spline working copy is going to change.
     */
    spline_changing(position = null) {
        this.stop_spline_playback();
        this.line.data.clear();
        if (position !== null && is_checked(this.livePreviewBtn)) {
            if (this.motorSelector.unselected) return
            const id = this.motorSelector.selected_index;
            this.api.live_preview(position, id);
        }
    }


    /**
     * Notify spline editor that with the new current state of the spline.
     */
    spline_changed(workingCopy) {
        this.history.capture(workingCopy);
        this.draw_current_spline();
    }


    /**
     * API call for spline playback in backend. Also starts transport cursor.
     */
    async play_current_spline() {
        if (this.motorSelector.unselected) {
            return;
        }

        const spline = this.history.retrieve();
        const id = this.motorSelector.selected_index;
        const loop = this.transport.looping;
        const offset = this.transport.position;
        const startTime = await this.api.play_spline(spline, id, loop, offset);
        this.transport.startTime = startTime + INTERVAL;
        this.transport.play();
        this.update_ui();
    }


    /**
     * API call for stoping spline playback for currently selected motor.
     */
    async stop_spline_playback() {
        if (!this.transport.paused) {
            await this.api.stop_spline_playback();
            this.transport.pause();
            this.update_ui();
        }
    }


    /**
     * API call for starting recording trajectory. Disables motors in back end.
     */
    async start_recording() {
        this.transport.record();
        this.line.data.clear();
        this.line.data.maxlen = Infinity;
        this.auto = true;
        this.drawer.clear();
        await this.api.disable_motors();
    }


    /**
     * API call for ending trajectory recording. Converts trajectory into
     * spline and draws it. Re-enables motors in back end.
     */
    async stop_recording() {
        this.transport.stop();
        this.auto = false;
        await this.api.enable_motors();
        if (!this.recordedTrajectory.length) {
            return;
        }

        const spline = await this.api.fit_spline(this.recordedTrajectory);
        clear_array(this.recordedTrajectory);
        this.load_spline(spline);
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
        this.spline_changed(newSpline);
    }


    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        const t = this.transport.move(msg.timestamp);

        if (this.motorSelector.unselected) {
            // In case ws message hits before motorSelector has received motors
            return
        }

        const actualValue = msg.values[this.motorSelector.actualValueIndex];
        if (this.transport.playing && t > this.transport.duration) {
            this.transport.stop();
            this.update_ui();
        }

        if (this.transport.paused) {
            this.line.data.popleft();
        } else {
            this.line.append_data([t, actualValue]);
        }

        if (this.transport.recording) {
            this.recordedTrajectory.push([t, actualValue]);
        }
    }
}

customElements.define("being-editor", Editor);