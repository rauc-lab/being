"use strict";
/**
 * Curver base class for live plotter and spline editor.
 */
import { BBox } from "/static/js/bbox.js";
import { History, } from "/static/js/history.js";
import { tick_space, } from "/static/js/layout.js";
import {
    divide_arrays,
} from "/static/js/math.js";
import {
    create_element,
} from "/static/js/svg.js";
import {
    cycle,
} from "/static/js/utils.js";
import { Line } from "/static/js/line.js";


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

/** View port margin on all sides */
const MARGIN = 50;


/**
 * Curver base class for Plotter and Editor.
 */
export class CurverBase extends HTMLElement {
    constructor(auto=true) {
        console.log("CurverBase.constructor");
        super();
        this.auto = auto;
        this.width = 1;
        this.height = 1;
        this.viewport = new BBox([0, -0.001], [1, 0.001]);
        this.trafo = new DOMMatrix();
        this.trafoInv = new DOMMatrix();
        this.lines = [];
        this.colorPicker = cycle(COLORS);
        this.init_elements();
    }


    /**
     * Add a new material icon button to toolbar (or any other parent_
     * element).
     *
     * @param innerHTML - Inner HTML text
     * @param title - Tooltip
     * @param id - Button ID.
     * @param parent_ - Parent HTML element to append the new button to.
     */
    add_button(innerHTML, title = "", id = "", parent_ = null) {
        if (parent_ === null) {
            parent_ = this.toolbar;
        }

        const btn = document.createElement("button");
        btn.classList.add("mdc-icon-button")
        btn.classList.add("material-icons")
        btn.classList.add("btn-black")
        btn.innerHTML = innerHTML;
        btn.title = title;
        btn.id = id;
        parent_.appendChild(btn);
        return btn;
    }


    /**
     * Add a spacing element to toolbar.
     */
    add_space_to_toolbar() {
        const span = document.createElement("span");
        span.classList.add("space");
        this.toolbar.appendChild(span);
        return span;
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

        this.main = document.createElement("div")
        this.main.classList.add("main")
        this.main.id = "main"

        // Toolbar
        this.toolbar = document.createElement("div");
        this.toolbar.classList.add("toolbar");

        // Canvas
        this.canvas = document.createElement("canvas");
        this.ctx = this.canvas.getContext("2d");
        this.ctx.lineCap = "round";  //"butt" || "round" || "square";
        this.ctx.lineJoin = "round";  //"bevel" || "round" || "miter";

        // SVG
        this.svg = create_element("svg");
        this.backgroundGroup = this.svg.appendChild(create_element("g"));
        this.backgroundGroup.id = "background-splines"
        this.transportGroup = this.svg.appendChild(create_element("g"));
        this.transportGroup.id = "cursor"
        this.splineGroup = this.svg.appendChild(create_element("g"));
        this.splineGroup.id = "selected-spline"
 
        this.graphs = document.createElement("div")
        this.graphs.classList.add("graphDiv")
        this.graphs.appendChild(this.canvas)
        this.graphs.appendChild(this.svg)

        this.main.append(this.toolbar, this.graphs)

        this.shadowRoot.append(link, this.main);
    }


    /**
     * Update viewport bounding box.
     */
    update_bbox() {
        this.viewport.reset();
        this.lines.forEach(line => {
            this.viewport.expand_by_bbox(line.calc_bbox());
        });
    }


    /**
     * Update viewport transformation.
     */
    update_trafo() {
        const [sx, sy] = divide_arrays([this.width - 2 * MARGIN, this.height - 2 * MARGIN], this.viewport.size);
        if (!isFinite(sx) || !isFinite(sy) || sx === 0 || sy === 0)
            return

        this.trafo = DOMMatrix.fromMatrix({
            a: sx,
            d: -sy,
            e: -sx * this.viewport.ll[0] + MARGIN,
            f: sy * (this.viewport.ll[1] + this.viewport.height) + MARGIN,
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
        this.canvas.width = this.width = this.shadowRoot.getElementById("main").clientWidth;
        this.canvas.height = this.height = this.clientHeight - this.toolbar.offsetHeight;
        this.graphs.style.height = this.height + "px"

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
        }, 100);
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
        tick_space(this.viewport.ll[0], this.viewport.ur[0]).forEach(x => {
            const pt = (new DOMPoint(x, 0)).matrixTransform(this.trafo);
            ctx.fillText(x.toPrecision(1), pt.x, origin.y + offset);
        });
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";   // top, middle, bottom
        tick_space(this.viewport.ll[1], this.viewport.ur[1]).forEach(y => {
            const pt = (new DOMPoint(0, y)).matrixTransform(this.trafo);
            ctx.fillText(y.toPrecision(1), origin.x - offset, pt.y);
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
