/**
 * @module widget Base class for HTML web component. Simple HTMLElement with a
 * toolbar div.
 */
import { add_option } from "/static/js/utils.js";
import { create_button } from "/static/js/button.js";


/**
 * Render template, clone it and append it to a target HTMLElement.
 *
 * @param {object or string} template Element or string
 * @param {*} target Target HTMLElement to append rendered template to.
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
 * @param {*} href Href link.
 * @param {*} target Target element to append link to.
 */
export function append_link_to(href, target) {
    const link = document.createElement("link");
    link.setAttribute("href", href);
    link.setAttribute("type", "text/css");
    link.setAttribute("rel", "stylesheet");
    target.appendChild(link);
}

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


export class WidgetBase extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
    }

    /**
     * Append HTML template to shadow root.
     *
     * @param {HTMLElement} template to add.
     */
    append_template(template) {
        append_template_to(template, this.shadowRoot);
    }

    /**
     * Add CSS stylesheet link to shadowroot.
     *
     * @param {String} href Path to CSS stylesheet.
     */
    append_link(href) {
        append_link_to(href, this.shadowRoot);
    }
};


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
     * @param innerHTML Inner HTML text
     * @param title Tooltip
     */
    add_button_to_toolbar(innerHTML, title = "") {
        const btn = create_button(innerHTML, title);
        this.toolbar.appendChild(btn);
        return btn;
    }

    /**
     * Add a spacing element to the toolbar.
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
     * @param {String} options Select options.
     * @param {String} name Select name and label.
     */
    add_select_to_toolbar(options = [], name = "") {
        const select = create_select(options, name);
        this.toolbar.appendChild(select);
        return select;
    }
}

customElements.define("being-widget", Widget);
