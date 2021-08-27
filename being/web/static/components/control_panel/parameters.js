import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";
import { clip } from "/static/js/math.js";


function make_editable(ele, on_change, validator=null, newLines=false) {
    if (validator === null) {
        validator = value => { return value; }
    }
    ele.addEventListener("dblclick", evt => {
        console.log("dbclick");
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


const INVALID = "INVALID";


customElements.define("being-slider", class BeingSlider extends HTMLElement {

    N_TICKS = 1000;

    constructor() {
        console.log("BeingSlider.constructor()");
        super();
        this.minValue = 0.0;
        this.maxValue = 1.0;
        this.fullname = '';
        this.init_elements();
    }

    get value() {
        return this.slider.value / this.N_TICKS * (this.maxValue - this.minValue) + this.minValue;
    }

    set value(value) {
        this.slider.value = (value - this.minValue) / (this.maxValue - this.minValue) * this.N_TICKS
        this.span.innerText = value.toFixed(1);
    }

    validate(text) {
        const num = parseFloat(text);
        if (isNaN(num)) {
            throw INVALID;
        }

        return clip(num, this.minValue, this.maxValue);
    }

    connectedCallback() {
        console.log("BeingSlider.connectedCallback()");
        this.slider.addEventListener("input", evt => {
            this.span.innerText = this.value.toFixed(1);
        });

        make_editable(this.span, 
            text => {
                this.value = parseFloat(text);
                this.emit();
            },
            text => { return this.validate(text) },
        );
    }

    init_elements() {
        this.attachShadow({ mode: "open" });
        this.slider = document.createElement("input");
        this.slider.type = "range";
        this.slider.min = 0;
        this.slider.max = this.N_TICKS;
        this.shadowRoot.appendChild(this.slider);
        this.span = document.createElement("span")
        this.shadowRoot.appendChild(this.span);
    }

    async emit() {
        const url = API + "/params/" + this.fullname;
        await put_json(url, this.value);
    }

    populate(param) {
        console.log("populate:", param)
        this.minValue = param.minValue;
        this.maxValue = param.maxValue;
        this.fullname = param.fullname;
        this.value = param.value;
        this.slider.addEventListener("change", async evt => {
            this.emit();
        });
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
                case "MotionSelection":
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
    console.log(container);
    console.log(params);
    populate(container, params, 1);
}