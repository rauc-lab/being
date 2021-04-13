/**
 * @module widget Base class for HTML web component. Simple HTMLElement with a
 * toolbar div.
 */
import { add_option } from "/static/js/utils.js";
import { create_button } from "/static/js/button.js";


export class Widget extends HTMLElement {
    constructor() {
        super();
        const root = this.attachShadow({ mode: "open" });
        this._append_link("static/css/material_icons.css");
        this._append_link("static/css/widget.css");
        this._append_link("static/css/toolbar.css");
        const toolbar = document.createElement("div");
        toolbar.classList.add("toolbar");
        this.toolbar = root.appendChild(toolbar);
    }

    /**
     * Add CSS stylesheet link to shadowroot.
     *
     * @param {String} href Path to CSS stylesheet.
     */
    _append_link(href) {
        const link = document.createElement("link");
        this.shadowRoot.appendChild(link);
        link.setAttribute("href", href);
        link.setAttribute("type", "text/css");
        link.setAttribute("rel", "stylesheet");
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
        this.toolbar.appendChild(select);
        return select;
    }

    /**
     * Add a HTML template to shadow root.
     * @param {HTMLElement} template to add.
     */
    add_template(template) {
        this.shadowRoot.appendChild(template.content.cloneNode(true));
    }
}

customElements.define("being-widget", Widget);
