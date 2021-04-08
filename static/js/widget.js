/**
 * Create new HTML button (material-icons class).
 *
 * @param {String} innerHTML Inner HTML of button.
 * @param {String} title Tooltip for button
 * @returns HTMLButton
 */
export function create_button(innerHTML, title = "") {
    const btn = document.createElement("button");
    btn.classList.add("material-icons");
    btn.innerHTML = innerHTML;
    btn.title = title;
    return btn;
}


export class Widget extends HTMLElement {
    constructor() {
        super();
        const root = this.attachShadow({ mode: "open" });

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
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", href);
    }

    /**
     * Add a new material icon button to toolbar (or any other parent_
     * element).
     *
     * @param innerHTML Inner HTML text
     * @param title Tooltip
     * @param id Button ID.
     * @param parent_ Parent HTML element to append the new button to.
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
     * @param {String} name Select name and label.
     * @param {String} options Select options.
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
}

customElements.define("being-widget", Widget);
