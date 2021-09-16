import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";
import { clip } from "/static/js/math.js";
import { remove_all_children } from "/static/js/utils.js";


const INVALID = "INVALID";


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


class ParamWidget extends HTMLElement {
    constructor() {
        super();
        this.fullname = "";
        this._value = null;
        this.attachShadow({ mode: "open" });
    }

    get value() {
        return this._value;
    }

    set value(value) {
        this._value = value;
    }

    populate(param) {
        this.fullname = param.fullname;
        this._value = param.value;
    }

    async emit() {
        const url = API + "/params/" + this.fullname;
        await put_json(url, this.value);
    }
}


customElements.define("being-slider", class BeingSlider extends ParamWidget {

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
        super.populate(param);
        this.minValue = param.minValue;
        this.maxValue = param.maxValue;
        this.slider.addEventListener("change", async evt => {
            this.emit();
        });
    }

    connectedCallback() {
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
});


customElements.define("being-single-selection", class BeingSingleSelection extends ParamWidget {
    constructor() {
        super();
        this.form = document.createElement("form");
        this.shadowRoot.appendChild(this.form);
    }

    populate(param) {
        super.populate(param);
        this.clear();
        param.possibilities.forEach((possibility, index) => {
            this.add_radio_label(possibility, index);
        });

        const query = "input[name=" + this.fullname + "][value=" + param.value + "]";
        this.form.querySelector(query).checked = true;
    }

    connectedCallback() {
        this.form.addEventListener("change", async evt => {
            const query = "input[name=" + this.fullname + "]:checked";
            this.value = this.form.querySelector(query).value;
            this.emit();
        });
    }

    clear() {
        remove_all_children(this.form);
    }

    add_radio_label(possibility, index) {
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
});


customElements.define("being-multi-selection", class BeingMultiSelection extends ParamWidget {
    constructor() {
        super();
        this.form = document.createElement("form");
        this.shadowRoot.appendChild(this.form);
    }

    populate(param) {
        super.populate(param);
        this.clear();
        param.possibilities.forEach((possibility, index) => {
            this.add_checkbox_label(possibility, index);
        });

        const query = "input[name=" + this.fullname + "]";
        this.form.querySelectorAll(query).forEach(ele => {ele.checked = true;});
    }

    connectedCallback() {
        this.form.addEventListener("change", async evt => {
            const query = "input[name=" + this.fullname + "]:checked";
            this.value = [];
            this.form.querySelectorAll(query).forEach(input => {
                this.value.push(input.value);
            });
            this.emit();
        });
    }

    clear() {
        remove_all_children(this.form);
    }

    add_checkbox_label(possibility, index) {
        const id = "single " + index;

        const input = document.createElement("input");
        input.type = "checkbox";
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
});


function populate(container, obj, level=1) {
    for (const [key, param] of Object.entries(obj)) {
        if (typeof param !== "object") {
            continue;
        }

        if (param.type === "Block") {
            const label = document.createElement("label");
            label.innerText = param.name;
            container.appendChild(label);
            switch (param.blockType) {
                case "Slider":
                    const slider = document.createElement('being-slider');
                    slider.populate(param);
                    container.appendChild(slider);
                    break;
                //case "MotionSelection":
                //    const motionSelection = document.createElement('being-motion-selection');
                //    motionSelection.populate(param);
                //    container.appendChild(motionSelection);
                //    break;
                case "SingleSelection":
                    const sel = document.createElement("being-single-selection");
                    sel.populate(param);
                    container.appendChild(sel);
                    break

                case "MultiSelection":
                    const mul = document.createElement("being-multi-selection");
                    mul.populate(param);
                    container.appendChild(mul);
                    break

                default:
                    const paragraph = document.createElement('p');
                    paragraph.innerText = param.blockType;
                    container.appendChild(paragraph);
            }

            container.appendChild(document.createElement("br"));

        } else {
            const heading = document.createElement('h' + level);
            heading.innerText = key;
            container.appendChild(heading);
            populate(container, param, level + 1);

        }

        if (typeof value === "object" && value !== null & value.type !== "Block") {
        } else {
        }
    }
}


export function init_parameters_elements(container, params) {
    console.log("init_parameters_elements()");
    populate(container, params, 1);
}
