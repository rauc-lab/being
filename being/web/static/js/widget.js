/**
 * Widget base class for being HTML web components. Simple HTMLElement with an
 * additional toolbar div.
 *
 * @module js/widget
 */
import { add_option } from "/static/js/utils.js";
import { create_button } from "/static/js/button.js";


/**
 * Render template, clone it and append it to a target HTMLElement.
 *
 * @param {HTMLTemplateElement|string} template - Template element or string.
 * @param {HTMLElement} target - Target element to append rendered template to.
 */
 export function append_template_to(template, target) {
    if (typeof template === "string") {
        let temp;
        temp = document.createElement("template");
        temp.innerHTML = template;
        template = temp;
    }

    const child = template.content.cloneNode(true);
    target.appendChild(child);
}


/**
 * Append CSS link node to target.
 *
 * @param {string} href - Href link.
 * @param {HTMLElement} target - Target element to append link to.
 */
export function append_link_to(href, target) {
    const link = document.createElement("link");
    link.setAttribute("href", href);
    link.setAttribute("type", "text/css");
    link.setAttribute("rel", "stylesheet");
    target.appendChild(link);
}


/**
 * Create select HTML element.
 *
 * @param {array} options - Name of initial options to add.
 * @param {string} name - Optional label string (not supported at the moment).
 *
 * @returns {HTMLSelectElement} New select element.
 */
export function create_select(options = [], name = "") {
    //const container = document.createElement("div");
    if (name !== "") {
        const label = document.createElement("label");
        label.innerHTML = name;
        label.setAttribute("for", name);
        //container.appendChild(label);
    }

    const select = document.createElement("select");
    select.setAttribute("name", name);
    options.forEach(opt => {
        add_option(select, opt);
    });
    //container.appendChild(select);
    //this.toolbar.appendChild(container);
    return select;
}


/**
 * Base class for Being widget.
 *
 * Simple web component with open shadow root. No toolbar.
 */
export class WidgetBase extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
    }

    /**
     * Append HTML template to shadow root.
     *
     * @param {HTMLTemplateElement | string} template - Template to add.
     */
    append_template(template) {
        append_template_to(template, this.shadowRoot);
    }

    /**
     * Add CSS stylesheet link to shadowroot.
     *
     * @param {string} href - Path to CSS stylesheet.
     */
    append_link(href) {
        append_link_to(href, this.shadowRoot);
    }
};


/**
 * Custom component being widget. With toolbar.
 */
export class Widget extends WidgetBase {
    constructor() {
        super();
        this.append_link("static/css/material_icons.css");
        this.append_link("static/css/widget.css");
        this.append_link("static/css/toolbar.css");
        const toolbar = document.createElement("div");
        toolbar.classList.add("toolbar");
        this.toolbar = this.shadowRoot.appendChild(toolbar);
    }

    /**
     * Add a new material icon button to toolbar (or any other parent_
     * element).
     *
     * @param {string} innerHTML - Inner HTML text
     * @param {string} [title= ] - Button tooltip.
     *
     * @returns {HTMLButton} Button element.
     */
    add_button_to_toolbar(innerHTML, title = "") {
        const btn = create_button(innerHTML, title);
        this.toolbar.appendChild(btn);
        return btn;
    }

    /**
     * Add a spacing element to the toolbar.
     *
     * @returns {HTMLSpanElement} Span element.
     */
    add_space_to_toolbar() {
        const span = document.createElement("span");
        span.classList.add("space");
        this.toolbar.appendChild(span);
        return span;
    }

    /**
     * Add a select element to the toolbar. 
     *
     * @param {string} options - Select options.
     * @param {string} [name= ] - Select name and label.
     *
     * @returns {HTMLSelectElement} Select element.
     */
    add_select_to_toolbar(options = [], name = "") {
        const select = create_select(options, name);
        this.toolbar.appendChild(select);
        return select;
    }
}

customElements.define("being-widget", Widget);
