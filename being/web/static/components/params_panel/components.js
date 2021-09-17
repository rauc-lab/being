import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";
import { clip } from "/static/js/math.js";
import { remove_all_children, clear_array } from "/static/js/utils.js";
import {append_template_to, append_link_to} from "/static/js/widget.js";


const INVALID = "INVALID";


/**
 * Make text field editable by double clicking it.
 * 
 * @param {*} ele Element to make editable.
 * @param {*} on_change On change event callback.
 * @param {*} validator Text content validator function.
 * @param {*} newLines If to accept new lines or not.
 */

function make_editable(ele, on_change, validator=null, newLines=false) {
    if (validator === null) {
        validator = value => { return value; }
    }

    ele.addEventListener("dblclick", evt => {
        ele.contentEditable = true;
        ele.focus();
    });

    let oldValue = null;
    function capture() {
        oldValue = ele.innerText;
    }

    function revert() {
        ele.innerText = oldValue;
    }

    ele.addEventListener("focus", evt => {
        capture();
    });

    ele.addEventListener("blur", evt => {
        ele.contentEditable = false;
    })

    ele.addEventListener("keyup", evt => { 
        if (evt.key === "Escape") {
            revert();
            ele.blur();
        } else if (evt.key === "Enter") {
            try {
                const validated = validator(ele.innerText);
                on_change(validated);
                ele.innerText = validated;
            }
            catch {
                revert();
            }

            ele.blur();
        }
    });

    if (!newLines) {
        ele.addEventListener("keypress", evt => {
            if (evt.key === "Enter") {
                evt.preventDefault();
            }
        })
    }
}


const PARAM_STYLE = `
<style>
    :host {
        display: block;
        break-inside: avoid-column;
        margin-bottom: 1em;
    }
</style>
`;


class Param extends HTMLElement {
    constructor() {
        super();
        this.name = "";
        this.fullname = "";
        this._value = null;

        this.attachShadow({ mode: "open" });

        append_template_to(PARAM_STYLE, this.shadowRoot);

        this.label = document.createElement("label");
        this.label.innerHTML = this.name;
        this.shadowRoot.appendChild(this.label);
    }

    get value() {
        return this._value;
    }

    set value(value) {
        this._value = value;
    }

    populate(param) {
        this.fullname = param.fullname;
        this.name = param.name;
        this.value = param.value;
        this.label.innerHTML = this.name;
    }

    async emit() {
        const url = API + "/params/" + this.fullname;
        await put_json(url, this.value);
    }
}

export class Slider extends Param {

    N_TICKS = 1000;

    constructor() {
        super();
        this.minValue = 0.0;
        this.maxValue = 1.0;

        this.slider = document.createElement("input");
        this.slider.type = "range";
        this.slider.min = 0;
        this.slider.max = this.N_TICKS;
        this.shadowRoot.appendChild(this.slider);

        this.span = document.createElement("span")
        this.shadowRoot.appendChild(this.span);
    }

    get value() {
        return this.slider.value / this.N_TICKS * (this.maxValue - this.minValue) + this.minValue;
    }

    set value(value) {
        this.slider.value = (value - this.minValue) / (this.maxValue - this.minValue) * this.N_TICKS
        this.span.innerText = value.toFixed(1);
    }

    populate(param) {
        this.minValue = param.minValue;
        this.maxValue = param.maxValue;
        super.populate(param);
    }

    connectedCallback() {
        this.slider.addEventListener("change", async evt => {
            this.emit();
        });

        this.slider.addEventListener("input", evt => {
            this.span.innerText = this.value.toFixed(1);
        });

        make_editable(this.span, 
            text => {
                this.value = parseFloat(text);
                this.emit();
            },
            text => {
                return this.validate(text);
            },
        );
    }

    validate(text) {
        const num = parseFloat(text);
        if (isNaN(num)) {
            throw INVALID;
        }

        return clip(num, this.minValue, this.maxValue);
    }
}


class Selection extends Param {
    constructor() {
        super();
        this.form = document.createElement("form");
        this.shadowRoot.appendChild(this.form);
    }

    connectedCallback() {
        this.form.addEventListener("change", async evt => {
            this.emit();
        });
    }

    populate(param) {
        this.fullname = param.fullname;
        this.possibilities = param.possibilities;
        remove_all_children(this.form);
        param.possibilities.forEach((possibility, index) => {
            this.add_entry(possibility, index);
        });
        super.populate(param);
    }

    base_query() {
        return `input[name="${this.fullname}"]`;
    }

    //add_entry(possibility, index) { }
}


export class SingleSelection extends Selection {
    add_entry(possibility, index) {
        const id = "single " + index;

        const input = document.createElement("input");
        input.type = "radio";
        input.id = id;
        input.name = this.fullname;
        input.value = possibility;
        this.form.appendChild(input);

        const label = document.createElement("label");
        label.for = id;
        label.innerHTML = possibility;
        this.form.appendChild(label);

        this.form.appendChild(document.createElement("br"));
    }

    get value() {
        const query = this.base_query() + ':checked';
        return this.form.querySelector(query).value;
    }

    set value(value) {
        const query = this.base_query() + '[value="' + value + '"]';
        this.form.querySelector(query).checked = true;
    }
}


export class MultiSelection extends Selection {
    add_entry(possibility, index) {
        const id = "multi" + index;

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = id;
        input.name = this.fullname;
        input.value = possibility;
        this.form.appendChild(input);

        const label = document.createElement("label");
        label.setAttribute("for", id);
        label.innerHTML = possibility;
        this.form.appendChild(label);

        this.form.appendChild(document.createElement("br"));
    }

    get value() {
        const value = []
        const query = this.base_query() + ':checked';
        this.form.querySelectorAll(query).forEach(input => {
            value.push(input.value);
        });

        return value;
    }

    set value(value) {
        const query = this.base_query();
        this.form.querySelectorAll(query).forEach(ele => {
            if (value.includes(ele.value)) {
                ele.checked = true;
            }
        });
    }

}

export class MotionSelection extends MultiSelection {}
