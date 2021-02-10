"use strict";
import {BBox} from "/static/js/bbox.js";


/**
 * Custom curver HTMLElement.
 *
 * Shadow root with canvas and SVG overlay.
 */
customElements.define('being-curver', class extends HTMLElement {
    constructor() {
        console.log("BeingCurver.constructor");
        super();
        this.size = [1, 1];
        this.bbox = new BBox([0, 0], [1, 1]);
        this.init_elements();
        //this.setup_canvas();
    }

    /**
     * Width in px.
     */
    get width() {
        return this.size[0];
    }

    /**
     * Height in px.
     */
    get height() {
        return this.size[1];
    }

    /**
     * Aspect ratio
     */
    get ratio() {
        return this.size[0] / this.size[1];
    }

    /**
     * Initialize shadow root with HTML elements.
     */
    init_elements() {
        console.log("BeingCurver.init_elements");
        this.attachShadow({mode: "open"});

        // Apply external styles to the shadow dom
        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/curver.css");

        // Attach the created element to the shadow dom
        this.canvas = document.createElement("canvas");
        this.ctx = this.canvas.getContext("2d");
        this.svg = document.createElement("svg");
        this.shadowRoot.append(link, this.canvas, this.svg);
    }

    /**
     * Resize elements. Mainly because of canvas because of lacking support for
     * relative sizes. Can be used as event handler with
     * `this.resize.bind(this)`.
     */
    resize() {
        console.log("BeingCurver.resize");
        this.size = [this.clientWidth, this.clientHeight];
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        // TODO: Update SVG
        //this.draw();
    }

    connectedCallback() {
        console.log("BeingCurver.connectedCallback");
        addEventListener("resize", this.resize.bind(this));
        setTimeout(this.resize.bind(this), 0);  // TODO: Hack for this.resize() which does not work
    }


    /**
     * Clear canvas.
     */
    clear_canvas() {
        this.ctx.resetTransform();
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
});
