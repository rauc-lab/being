/**
 * @module curver Curver base class for live plotter and spline editor.
 */
import { Widget } from "/static/js/widget.js";
import { BBox } from "/static/js/bbox.js";
import { tick_space, } from "/static/js/layout.js";
import { divide_arrays} from "/static/js/array.js";
import { clip } from "/static/js/math.js";
import { cycle } from "/static/js/utils.js";


/** @const {array} - Default line colors */
const COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
];

/** @const {number} - View port margin on all sides */
const MARGIN = 50;

/** @const {BBox} - Minimum sized bounding box for viewport */
const MIN_VIEWPORT = new BBox([Infinity, -0.001], [-Infinity, 0.001]);

/** @const {HTMLElement} - Curver base template */
const CURVER_TEMPLATE = document.createElement("template");
CURVER_TEMPLATE.innerHTML = `
<div class="container">
    <div id="motion-list"></div>
    <div id="graph">
        <canvas id="canvas">
            Your browser doesn't support the HTML5 canvas tag.
        </canvas>
        <svg id="svg" xmlns="http://www.w3.org/2000/svg">
            <g id="background"></g>
            <g id="cursor"></g>
            <g id="main"></g>
        </svg>
    </div>
</div>
`;


/**
 * Curver base class for Plotter and Editor.
 */
export class CurverBase extends Widget {
    constructor(auto = true) {
        super();
        this.auto = auto;
        this.viewport = MIN_VIEWPORT.copy();
        this.trafo = new DOMMatrix();
        this.trafoInv = new DOMMatrix();
        this.lines = [];
        this.colorPicker = cycle(COLORS);
        this.init_elements();
    }

    connectedCallback() {
        addEventListener("resize", () => this.resize());
        this.resize();
        //this.run();
        //setTimeout(() => this.resize(), 1);
        setTimeout(() => {
            this.resize();
            this.run();
        }, 100);
    }

    /**
     * Initialize DOM elements with shadow root.
     */
    init_elements() {
        this._append_link("static/css/curver.css");
        this.add_template(CURVER_TEMPLATE);

        this.graph = this.shadowRoot.getElementById("graph");
        this.canvas = this.shadowRoot.getElementById("canvas");
        this.svg = this.shadowRoot.getElementById("svg");
        this.splineGroup = this.shadowRoot.getElementById("main")
        this.transportGroup = this.shadowRoot.getElementById("cursor")
        this.backgroundGroup = this.shadowRoot.getElementById("background")
        this.motionListDiv = this.shadowRoot.getElementById("motion-list")

        this.ctx = this.canvas.getContext("2d");
        this.ctx.lineCap = "round";  //"butt" || "round" || "square";
        this.ctx.lineJoin = "round";  //"bevel" || "round" || "miter";
    }

    /**
     * Reset viewport to MIN_VIEWPORT.
     */
    reset_viewport() {
        this.viewport = MIN_VIEWPORT.copy();
    }

    /**
     * Update viewport bounding box.
     */
    update_bbox() {
        this.reset_viewport();
        this.lines.forEach(line => {
            this.viewport.expand_by_bbox(line.calc_bbox());
        });
    }

    /**
     * Update viewport transformation.
     */
    update_trafo() {
        const width = this.graph.clientWidth;
        const height = this.graph.clientHeight;
        const [sx, sy] = divide_arrays([width - 2 * MARGIN, height - 2 * MARGIN], this.viewport.size);
        if (!isFinite(sx) || !isFinite(sy) || sx === 0 || sy === 0) {
            return;
        }

        this.trafo = DOMMatrix.fromMatrix({
            a: sx,
            d: -sy,
            e: -sx * this.viewport.ll[0] + MARGIN,
            f: sy * (this.viewport.ll[1] + this.viewport.height) + MARGIN,
        });
        this.trafoInv = this.trafo.inverse();
        this.ctx.setTransform(this.trafo);
        //this.svg.g.setAttribute("transform", this.trafo.toString());  // Sadly not working because of skewed aspect ratio :(
    }

    /**
     * Resize elements. Mainly because of canvas because of lacking support for
     * relative sizes. Can be used as event handler with
     * `this.resize.bind(this)`.
     */
    resize() {
        this.canvas.width = this.graph.clientWidth;
        this.canvas.height = this.graph.clientHeight;

        // Flip y-axis
        //const mtrx = [1, 0, 0, -1, 0, this.canvas.height];
        //this.ctx.setTransform(...mtrx);
        this.ctmInv = this.svg.getScreenCTM().inverse();

        this.update_trafo();
        this.draw_lines();
    }

    /**
     * Coordinates of mouse event inside canvas / SVG data space.
     * @param {MouseEvent} evt Mouse event to transform into data space.
     * @return {array} Coordinate point.
     */
    mouse_coordinates(evt) {
        const rect = this.canvas.getBoundingClientRect();
        const x = evt.clientX - rect.left;
        const y = evt.clientY - rect.top;
        const pt = (new DOMPoint(x, y)).matrixTransform(this.trafoInv);
        return [pt.x, pt.y];
    }

    /**
     * Transform a data point -> view space.
     * @param {array} pt 2d data point.
     * @return {array} Tranformed 2d point.
     */
    transform_point(pt) {
        const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
        return [ptHat.x, ptHat.y];
    }

    /**
     * Transform multiple data point into view space.
     * @param {array} pts Array of 2d data points.
     * @return {array} Array of 2d transformed points.
     */
    transform_points(pts) {
        return pts.map(pt => {
            const ptHat = (new DOMPoint(...pt)).matrixTransform(this.trafo);
            return [ptHat.x, ptHat.y];
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
     * @param {string} color Axis and tick label color.
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

        // Round for crisper lines
        origin.x = Math.round(origin.x);
        origin.y = Math.round(origin.y);

        ctx.moveTo(MARGIN, origin.y);
        ctx.lineTo(this.canvas.width - MARGIN, origin.y);
        ctx.moveTo(origin.x, MARGIN);
        ctx.lineTo(origin.x, this.canvas.height - MARGIN);
        ctx.stroke();

        // Draw ticks
        const offset = 3;
        ctx.font = ".8em Helvetica";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";   // top, middle, bottom
        tick_space(this.viewport.ll[0], this.viewport.ur[0]).forEach(x => {
            const pt = (new DOMPoint(x, 0)).matrixTransform(this.trafo);
            ctx.fillText(x, pt.x, clip(pt.y + offset, 0, this.canvas.height - MARGIN));
        });
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";   // top, middle, bottom
        tick_space(this.viewport.ll[1], this.viewport.ur[1]).forEach(y => {
            const pt = (new DOMPoint(0, y)).matrixTransform(this.trafo);
            ctx.fillText(y, clip(pt.x - offset, MARGIN, this.canvas.width), pt.y);
        });

        ctx.restore();
    }

    /**
     * Draw all line artists.
     */
    draw_lines() {
        //console.log("CurverBase.draw()");
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
    render() {
        this.draw_lines();
        window.requestAnimationFrame(() => this.render());
    }

    /**
     * Start rendering.
     */
    run() {
        requestAnimationFrame(() => this.render());
    }
}