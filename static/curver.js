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
    constructor(ctx, color = COLORS[0], maxlen = 1000, lineWidth = 2) {
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
    constructor(auto = true) {
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
        this.attachShadow({ mode: "open" });

        // Apply external styles to the shadow dom
        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/curver.css");

        const materialCss = document.createElement("link");
        materialCss.setAttribute("rel", "stylesheet");
        materialCss.setAttribute("href", "https://fonts.googleapis.com/icon?family=Material+Icons");

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

        this.graphs = document.createElement("div")
        this.graphs.classList.add("graphDiv")
        this.graphs.appendChild(this.canvas)
        this.graphs.appendChild(this.svg)

        this.shadowRoot.append(link, materialCss, this.toolbar, this.graphs);
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
        this.canvas.height = this.height = this.clientHeight - this.toolbar.offsetHeight;
        this.graphs.style.height = this.height + "px"

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
        }, 100);
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
    draw_axis_and_tick_labels(color = "silver") {
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
        this.isRecording = false;

        const rec = document.createElement("button");
        rec.classList.add("btn-black")
        rec.classList.add("mdc-icon-button")
        rec.classList.add("material-icons")
        rec.id = "btn-rec"
        rec.innerHTML = "circle";
        rec.title = "Record Signal"
        var self = this;
        rec.addEventListener("click", e => self.record_signal(rec))
        this.toolbar.appendChild(rec);
    }

    /**
     * Record selected signal 
     */
    record_signal(el) {
        this.isRecording = !this.isRecording
        if (this.isRecording) {
            el.classList.add("recording")
            // TODO: Start recorder
        }
        else {
            el.classList.remove("recording")
            //TOOD: Remove recorder
        }
    }
}


customElements.define('being-plotter', Plotter);


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
        this.isPlaying = false;
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

        const selMotDiv = document.createElement("div")
        selMotDiv.classList.add("btn-black")
        const selMot = document.createElement("select");
        selMot.id = "select-motor"
        const label = document.createElement("label")
        label.innerHTML = "Motion Player: "
        label.for = "select-motor"
        selMot.addEventListener("click", e => self.select_motor(selMot))
        selMotDiv.appendChild(label)
        selMotDiv.appendChild(selMot)
        this.toolbar.appendChild(selMotDiv);

        // TODO : Toggle button start / stop
        const play = document.createElement("button")
        play.classList.add("btn-black")
        play.classList.add("mdc-icon-button")
        play.classList.add("material-icons")
        play.title = "Play spline on motor"
        play.innerHTML = "play_circle"
        play.addEventListener("click", e => self.play_motion(play))
        this.toolbar.appendChild(play)

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

    save_spline(el) {
        // TODO: 

    }

    select_motor(el) {
        // TODO: 

    }

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

    resize() {
        super.resize();
        this.draw_spline();
    }

    transform_points(pts) {
        return pts.map(pt => {
            const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
            return [ptHat.x, ptHat.y];
        });
    }

    load_spline(spline) {
        const cps = bpoly_to_bezier(spline);
        this.init_spline(cps);
    }

    create_path(data, strokeWidth = 1, color = "black") {
        const path = create_element('path');
        setattr(path, "stroke", color);
        setattr(path, "stroke-width", strokeWidth);
        setattr(path, "fill", "transparent");
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(data)));
        };

        return path
    }

    init_spline(cps) {
        this.bbox = fit_bbox(cps.flat(1));
        this.update_trafo();
        remove_all_children(this.svg);
        cps.forEach((pts, i) => {
            let path = this.create_path(pts);
            this.svg.appendChild(path);
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