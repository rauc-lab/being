"use strict";
/**
 * Spline list as custom HTML element.
 */

 export class SplineList extends HTMLElement {
    constructor() {
        super();
        this.init_elements();
    }

    /**
     * Initialize DOM elements with shadow root.
     */
    init_elements() {
        this.attachShadow({ mode: "open" });

        // Apply external styles to the shadow dom
        // const link = document.createElement("link");
        // link.setAttribute("rel", "stylesheet");
        // link.setAttribute("href", "static/curver/spline_list.css");

        this.list= document.createElement("ul");
        const testObj = document.createElement("li")
        testObj.innerHTML = "file.json"
        this.list.appendChild(testObj)

        this.shadowRoot.append( this.list);
        console.log("attach spline list")
    }
 }

 customElements.define('being-spline-list', SplineList);