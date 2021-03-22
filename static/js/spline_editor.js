"use strict";
/**
 * Spline editor custom HTML element.
 */
import { BBox } from "/static/js/bbox.js";
import { CurverBase } from "/static/js/curver.js";
import { make_draggable } from "/static/js/draggable.js";
import { History } from "/static/js/history.js";
import { subtract_arrays, clip } from "/static/js/math.js";
import { BPoly } from "/static/js/spline.js";
import { fetch_json, clear_array } from "/static/js/utils.js";
import { Line } from "/static/js/line.js";
import { PAUSED, PLAYING, RECORDING, Transport } from "/static/js/transport.js";
import { SplineDrawer } from "/static/js/spline_drawer.js";
import { SplineList } from "/static/js/spline_list.js";
import { API, INTERVAL } from "/static/js/config.js";
import { MotorSelector } from "/static/js/motor_selector.js";
import { toggle_button, switch_button_on, switch_button_off, is_checked, enable_button, disable_button } from "/static/js/button.js";


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


function put(url) { return fetch(url, {method: "PUT"}) }
function post(url) { return fetch(url, {method: "POST"}) }
function get_json(url) { return fetch_json(url, "GET"); }
function post_json(url, data) { return fetch_json(url, "POST", data); }
function put_json(url, data) { return fetch_json(url, "PUT", data); }


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
        this.dataBbox = DEFAULT_DATA_BBOX.copy();
        this.transport = new Transport(this);
        this.drawer = new SplineDrawer(this, this.splineGroup);
        this.backgroundDrawer = new SplineDrawer(this, this.backgroundGroup);
        this.motorSelector = null;  // Gets initialized inside setup_toolbar_elements(). Not nice but...
        this.splineList = new SplineList(this);
        this.splineList.fetch_splines().then(() =>
            this.splineList.update_spline_list()
        )
        this.trajectory = [];

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
        get_json(API + "/motors").then(motorInfos => {
            this.motorSelector.populate(motorInfos);
        });
        this.load_spline(ZERO_SPLINE);
        return;
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
            this.update_trafo();
            this.draw();
        });
        this.add_button("zoom_out", "Zoom Out").addEventListener("click", evt => {
            zoom_bbox_in_place(this.viewport, 1 / ZOOM_FACTOR_PER_STEP);
            this.update_trafo();
            this.draw();
        });
        this.add_button("zoom_out_map", "Reset zoom").addEventListener("click", evt => {
            this.viewport = this.dataBbox.copy();
            this.update_trafo();
            this.draw();
        });

        this.add_space_to_toolbar();

        // Motor selection
        const select = this.add_select();
        select.addEventListener("change", evt => {
            this.stop_all_spline_playbacks();
        });
        this.motorSelector = new MotorSelector(select);

        this.add_space_to_toolbar();

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

        this.livePreviewBtn = this.add_button("precision_manufacturing", "Toggle live preview of knot position on the motor");
        this.livePreviewBtn.addEventListener("click", evt => {
            toggle_button(this.livePreviewBtn);
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
        const bbox = spline.bbox();
        bbox.expand_by_bbox(DEFAULT_DATA_BBOX);
        this.dataBbox = bbox;
        this.viewport = this.dataBbox.copy();
        this.update_trafo();
        this.draw_current_spline();
    }


    /**
     * Draw current version of spline from history.
     */
    draw_current_spline() {
        this.drawer.clear();
        const current = this.history.retrieve();
        const duration = current.end;
        this.transport.duration = duration;
        this.line.maxlen = .8 * duration / INTERVAL;
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
            this.live_preview(position);
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
        const url = this.motorSelector.selected_motor_url() + "/play";
        const spline = this.history.retrieve();
        const res = await post_json(url, {
            "spline": spline.to_dict(),
            "loop": this.transport.looping,
            "offset": this.transport.position,
        });
        this.transport.startTime = res["startTime"] + INTERVAL;  // +INTERVAL for better line matching
        this.transport.play();
        this.update_ui();
    }

    /**
     * API call for stoping spline playback for currently selected motor.
     */
    async stop_spline_playback() {
        if (!this.transport.paused) {
            this.transport.pause();
            this.update_ui();
            const url = this.motorSelector.selected_motor_url() + "/stop";
            await post(url);
        }
    }

    /**
     * API call for stoping all spline playback in being for all known motors.
     */
    async stop_all_spline_playbacks() {
        this.transport.pause();
        this.update_ui();
        await post(API + "/motors/stop");
    }

    /**
     * API call for setting live preview position value to back end.
     *
     * @param {Number} position Vertical y position of linear motor.
     */
    async live_preview(position) {
        const url = this.motorSelector.selected_motor_url() + "/livePreview";
        await put_json(url, {"position": position});
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
        await put(API + "/motors/disenable");
    }

    /**
     * API call for ending trajectory recording. Converts trajectory into
     * spline and draws it. Re-enables motors in back end.
     */
    async stop_recording() {
        this.transport.stop();
        this.auto = false;
        await put(API + "/motors/enable");
        if (!this.trajectory.length) {
            return;
        }

        const obj = await post_json(API + "/fit_spline", this.trajectory);
        clear_array(this.trajectory);
        const spline = BPoly.from_object(obj);
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
            this.trajectory.push([t, actualValue]);
        }
    }
}

customElements.define("being-editor", Editor);
