/**
 * @module spline_editor Spline editor custom HTML element.
 */
import {Api} from "/static/js/api.js";
import {subtract_arrays, array_reshape, multiply_scalar, array_shape } from "/static/js/array.js";
import {BBox} from "/static/js/bbox.js";
import {toggle_button, switch_button_on, switch_button_off, is_checked, enable_button, disable_button, switch_button_to} from "/static/js/button.js";
import {INTERVAL} from "/static/js/config.js";
import {make_draggable} from "/static/js/draggable.js";
import {History} from "/static/js/history.js";
import {clip} from "/static/js/math.js";
import {COEFFICIENTS_DEPTH, zero_spline, BPoly} from "/static/js/spline.js";
import {clear_array, insert_after} from "/static/js/utils.js";
import {CurverBase} from "/static/components/editor/curver.js";
import {Line} from "/static/components/editor/line.js";
import { OldMotionList, CurveList } from "/static/components/editor/curve_list.js";
import {MotorSelector} from "/static/components/editor/motor_selector.js";
import {CurveDrawer} from "/static/components/editor/drawer.js";
import {PAUSED, PLAYING, RECORDING, Transport} from "/static/components/editor/transport.js";
import { Widget, append_template_to } from "/static/js/widget.js";



/** @const {number} - Magnification factor for one single click on the zoom buttons */
const ZOOM_FACTOR_PER_STEP = 1.5;

/** @const {string} - Folded motion / spline list HTML attribute */
const FOLDED = "folded";

/** @const {Number} - Default spline knot shift offset amount...  */
const DEFAULT_KNOT_SHIFT = 0.5;


/**
 * Zoom / scale bounding box.
 *
 * @param {Bbox} bbox Bounding box to scale.
 * @param {Number} factor Zoom factor.
 */
function zoom_bbox(bbox, factor) {
    const zoomed = bbox.copy();
    const mid = .5 * (bbox.left + bbox.right);
    zoomed.left = 1 / factor * (bbox.left - mid) + mid;
    zoomed.right = 1 / factor * (bbox.right - mid) + mid;
    return zoomed;
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



const EDITOR_TEMPLATE = `
<style>
    :host {
        min-height: 50vh;
        display: flex;
        flex-flow: column;
    }
    .container {
        display: flex;
        flex-flow: row;
        align-items: strech;
        flex-grow: 1;
    }
    being-curve-list {
        flex-grow: 0;
    }

    being-curve-drawer {
        flex-grow: 1;
        border: none;
    }

    [folded] {
        display: none;
    }

</style>
<div class="container">
    <being-curve-list id="curve-list"></being-curve-list>
    <being-curve-drawer id="plotter"></being-curve-drawer>
</div>
`;


/**
 * Motion editor.
 *
 * Shadow root with canvas and SVG overlay.
 */
export class Editor extends Widget {
    constructor() {
        super();
        //this._append_link("static/components/editor/motion_editor.css");
        this.append_template(EDITOR_TEMPLATE)
        this.api = new Api();
        this.history = new History();
        this.list = this.shadowRoot.querySelector("being-curve-list");
        this.drawer = this.shadowRoot.querySelector("being-curve-drawer");
        this.transport = new Transport(this.drawer);
        this.interval = null;
        this.notificationCenter = null;

        this.motionPlayerSelect = null;
        this.channelSelect = null;
        this.setup_toolbar_elements();

        this.motorSelector = new MotorSelector(this.motionPlayerSelect, this.channelSelect);
        this.recordedTrajectory = [];

        this.update_ui();
    }

    async connectedCallback() {
        const config = await this.api.get_config();
        this.interval = config["Web"]["INTERVAL"];

        // Motor selector
        await this.motorSelector.init();
        this.motorSelector.addEventListener("change", () => {
            console.log("motorSelector changed");
            this.update_default_bbox();
            this.draw_current_spline();
            const mp = this.motorSelector.selected_motion_player();
            this.list.associate_motion_player_with_current_curve(mp);
        })

        // Curve list
        this.list.newBtn.addEventListener("click", evt => {
            console.log("New button clicked (not implemented at the moment)");
        });
        this.list.deleteBtn.addEventListener("click", evt => {
            console.log("Delete button clicked (not implemented at the moment)");
        });
        this.list.duplicateBtn.addEventListener("click", evt => {
            console.log("Duplicate button clicked (not implemented at the moment)");
        });
        this.list.addEventListener("change", () => {
            console.log("MotionEditor: list changed");
            if (this.confirm_unsaved_changes()) {
                const mp = this.list.associated_motion_player();
                this.motorSelector.select_motion_player(mp);

                // Draw foreground and background curves
                this.drawer.clear();
                const selected = this.list.selected;
                //console.log("MotionEditor: selected curve:", selected);
                //console.log("Going through all curves");
                for (const [name, curve] of this.list.curves.entries()) {
                    if (name === selected) {
                        //console.log(name, '-> load_spline()');
                        //this.drawer.draw_spline(curve, true);
                        this.load_spline(curve);
                    } else if (this.list.is_armed(name)) {
                        this.drawer.draw_spline(curve);
                    }
                }
                this.update_default_bbox()
                this.drawer.draw_curves();
                /*
                const curve = this.list.curves.get(name);
                this.draw_spline
                console.log(name, curve);
                */
            }
        });

        this.update_default_bbox();

        // Drawer stuff
        // SVG event listeners
        this.drawer.svg.addEventListener("click", evt => {
            this.drawer.clear_lines();
            const pt = this.drawer.mouse_coordinates(evt);
            this.transport.position = pt[0];
            this.transport.draw_cursor();
            if (this.transport.playing) {
                this.play_current_spline();
            }
        });
        this.drawer.svg.addEventListener("dblclick", evt => {
            // TODO: How to prevent accidental text selection?
            //evt.stopPropagation()
            //evt.preventDefault();
            this.stop_spline_playback();
            this.insert_new_knot(evt);
        });

        this.setup_keyboard_shortcuts();

        this.drawer.addEventListener("curvechanging", evt => {
            this.spline_changing(evt.detail.position);
        });
        this.drawer.addEventListener("curvechanged", evt => {
            this.spline_changed(evt.detail.newCurve);
        });

        if (this.list.selected !== null) {
            const curve = this.list.selected_curve();
            this.load_spline(curve);
        }

        this.toggle_limits();  // Enable by default
    }

    /**
     * Register notification center.
     */
    set_notification_center(notificationCenter) {
        this.notificationCenter = notificationCenter;
    }

    /**
     * Update size of default bounding box (or minimal bounding box).
     */
    update_default_bbox() {
        this.defaultBbox = new BBox([0., 0.], [1., 0.]);
        if (this.motorSelector.is_motion_player_selected()) {
            const motionPlayer = this.motorSelector.selected_motion_player();
            motionPlayer.motors.forEach(motor => {
                this.defaultBbox.expand_by_point([0., motor.length]);
            });
        }
    }


    /**
     * Toggle snapping to grid inside drawer.
     */
    toggle_snap_to_grid() {
        const opposite = !this.drawer.snapping_to_grid;
        this.drawer.snapping_to_grid = opposite;
        switch_button_to(this.snapBtn, opposite);
    }

    /**
     * Toggle c1 continuity in drawer.
     */
    toggle_c1() {
        console.log("Editor.toggle_c1()");
        const opposite = !this.drawer.c1;
        console.log("new value:", opposite);
        this.drawer.c1 = opposite;
        switch_button_to(this.c1Btn, !opposite);
    }


    /**
     * Toggle limiting curve control points for the given motion player / motors.
     * TODO: This has to be changed if the motion player changes!
     */
    toggle_limits() {
        const opposite = !is_checked(this.limitBtn);
        if (opposite) {
            const limited = new BBox([0, 0], [Infinity, 0.001]);
            const motionPlayer = this.motorSelector.selected_motion_player();
            motionPlayer.motors.forEach(motor => {
                limited.expand_by_point([Infinity, motor.length]);
            });
            this.drawer.limits = limited;
        } else {
            const noLimits = new BBox([0, -Infinity], [Infinity, Infinity]);
            this.drawer.limits = noLimits;
        };

        switch_button_to(this.limitBtn, opposite);
    }

    /**
     * Populate toolbar with buttons and motion planner / motor selections.
     * Wire up event listeners.
     */
    setup_toolbar_elements() {
        // Toggle motion list
        this.listBtn = this.add_button_to_toolbar("list", "Toggle spline list");
        this.listBtn.addEventListener("click", () => {
            this.list.toggleAttribute(FOLDED);
            this.update_ui();
            this.drawer.resize();
        });
        this.add_space_to_toolbar();


        // Editing history buttons
        this.newBtn = this.add_button_to_toolbar("add_box", "Create new spline");
        //this.newBtn.style.display = "none";
        this.newBtn.addEventListener("click", () => {
            this.create_new_spline();
        });
        this.saveBtn = this.add_button_to_toolbar("save", "Save motion");
        this.saveBtn.addEventListener("click", async () => {
            if (!this.history.length) {
                return;
            }

            const spline = this.history.retrieve();
            const name = this.list.selected;
            await this.api.update_spline(name, spline);
            this.history.clear();
            this.history.capture(spline);
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
            const zoomedIn = zoom_bbox(this.drawer.viewport, ZOOM_FACTOR_PER_STEP);
            this.drawer.change_viewport(zoomedIn);
        });
        this.add_button_to_toolbar("zoom_out", "Zoom out").addEventListener("click", () => {
            const zoomedOut = zoom_bbox(this.drawer.viewport, 1 / ZOOM_FACTOR_PER_STEP);
            this.drawer.change_viewport(zoomedOut);
        });
        this.add_button_to_toolbar("zoom_out_map", "Reset zoom").addEventListener("click", () => {
            if (!this.history.length) {
                return;
            }

            const current = this.history.retrieve();
            const bbox = current.bbox();
            bbox.expand_by_bbox(this.defaultBbox);
            this.drawer.change_viewport(bbox);
        });
        this.add_space_to_toolbar();


        // Motor selection
        this.motionPlayerSelect = this.add_select_to_toolbar();


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
        this.channelSelect = this.add_select_to_toolbar();
        this.snapBtn = this.add_button_to_toolbar("grid_3x3", "Snap to grid");  // TODO: Or vertical_align_center?
        this.snapBtn.addEventListener("click", () => this.toggle_snap_to_grid());

        this.c1Btn = this.add_button_to_toolbar("timeline", "Break continous knot transitions");
        this.c1Btn.addEventListener("click", () => this.toggle_c1());

        this.limitBtn = this.add_button_to_toolbar("fence", "Limit motion to selected motor");
        this.limitBtn.addEventListener("click", () => this.toggle_limits());

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
            const motionPlayer = this.motorSelector.selected_motion_player();
            this.spline_changed(zero_spline(motionPlayer.ndim));
        });

        this.add_space_to_toolbar()

        // Upload button. It is murky...
        const form = document.createElement("form");
        form.setAttribute("action", "api/upload-curves");
        form.setAttribute("method", "post");
        form.setAttribute("enctype", "multipart/form-data");
        //form.setAttribute("accept-charset", "utf-8");
        const templateStr = `
        <label for="file-upload" class="mdl-button mdl-js-button mdl-button--icon mdl-button--file">
            <i id="file-upload-button" class="material-icons"
                title="Upload some motions. Multiple .json or .zip files."
            >file_upload</i>
            <input
                type="file"
                id="file-upload"
                name="files"
                accept=".json, .zip"
                multiple="multiple"
                onchange="//this.form.submit();"
                hidden
            ></input>
        </label>
        `;
        append_template_to(templateStr, form);
        const fileinput = form.querySelector("input[type='file']")
        fileinput.addEventListener("change", async evt => {
            console.log('this change:');
            //evt.target.form.submit();
            form.dispatchEvent(new Event('submit'));
        });
        form.addEventListener("submit", async evt => {
            console.log("this submit");
            evt.preventDefault();
            const resp = await fetch(form.action, {
                method: form.method,
                body: new FormData(form),
            });
            console.log("resp:", resp);
            const notifications = await resp.json();
            /*
            for (let i in notis) {
                const dct = notis[i];
                console.log("dct:", dct);
                this.notificationCenter.notify(dct.message, dct.type)
                await sleep(0.5);
            }
            */
            if (this.notificationCenter !== null) {
                notifications.forEach(async dct => {
                    this.notificationCenter.notify(dct.message, dct.type, 3.5);
                });
            }
        });

        this.toolbar.appendChild(form);
        //this.add_button_to_toolbar("file_upload", "Upload some motions");
        const btn = this.add_button_to_toolbar("file_download", "Download all motions as a Zip archive");
        btn.addEventListener("click", async evt => {
            // https://stackoverflow.com/questions/3749231/download-file-using-javascript-jquery
            const resp = await this.api.download_all_curves_as_zip();
            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'being-content.zip' // the filename you want
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
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
                        this.toggle_snap_to_grid();
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
        throw "Deprecated Error";
        this.draw_lines();
        this.drawer.draw();
        this.backgroundDrawer.draw();
        this.transport.draw_cursor();
    }

    /**
     * Update UI elements. Mostly buttons at this time. Disabled state of undo
     * / redo buttons according to history.
     */
    update_ui() {
        switch_button_to(this.listBtn, !this.list.hasAttribute(FOLDED));

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
                throw "Ooops, something went wrong with the transport FSM!";
        }

        switch_button_to(this.loopBtn, this.transport.looping);
        switch_button_to(this.snapBtn, this.drawer.snapping_to_grid);
        switch_button_to(this.c1Btn, !this.drawer.c1);
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

        this.drawer.viewport.ll[1] = Math.min(this.viewport.ll[1], current.min);
        this.drawer.viewport.ur[1] = Math.max(this.viewport.ur[1], current.max);
        this.drawer.update_transformation_matrices();

        const duration = current.end;
        this.transport.duration = duration;
        this.drawer.maxlen = 0.9 * duration / this.interval;
        this.drawer.clear();
        {
            const interactive = true;
            const dim = this.motorSelector.selected_motor_channel();
            this.drawer.draw_spline(current, interactive, dim);
            this.drawer.draw();
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
        this.drawer.clear_lines();
        if ((position !== null) && is_checked(this.livePreviewBtn)) {
            const motionPlayer = this.motorSelector.selected_motion_player();
            const channel = this.motorSelector.selected_motor_channel();
            const [x, y] = position;
            this.transport.position = x;
            this.transport.draw_cursor();
            this.api.live_preview(y, motionPlayer.id, channel);
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
     * Start playback of current spline in back end.
     */
    async play_current_spline() {
        const spline = this.history.retrieve();
        const motionPlayer = this.motorSelector.selected_motion_player();
        const loop = this.transport.looping;
        const offset = this.transport.position;
        const startTime = await this.api.play_spline(spline, motionPlayer.id, loop, offset);
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
        this.drawer.lines.forEach(line => {
            line.data.clear();
            line.data.maxlen = Infinity;
        });
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

        const pos = this.drawer.mouse_coordinates(evt);
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
            const motionPlayer = this.motorSelector.selected_motion_player();
            const name = await this.api.find_free_name();
            const spline = zero_spline(motionPlayer.ndim);
            console.log(spline);
            await this.api.create_spline(name, spline);
            this.load_spline(spline);
            this.update_ui();
            this.list.add_entry(name, spline);
            this.list.select(name);
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

        const outputIndices = this.motorSelector.selected_value_output_indices();
        if (this.transport.paused) {
            this.drawer.forget();
        } else {
            outputIndices.forEach(idx => {
                const actualValue = msg.values[idx];
                this.drawer.plot_value(t, actualValue, idx);
            });
        }
        this.drawer.draw();

        if (this.transport.recording) {
            const vals = [];
            outputIndices.forEach(idx => {
                vals.push(msg.values[idx]);
            });
            this.recordedTrajectory.push([t].concat(vals));
        }
    }

    new_behavior_message(behavior) {
        return
        if (behavior.active) {
            this.transport.stop();
            this.update_ui();
        }
    }
}

customElements.define("being-editor", Editor);
