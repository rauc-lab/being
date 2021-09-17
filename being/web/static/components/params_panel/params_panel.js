import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";
import { clip } from "/static/js/math.js";
import { Widget } from "/static/js/widget.js";
import { remove_all_children, clear_array } from "/static/js/utils.js";
import { Slider, SingleSelection, MultiSelection, MotionSelection } from "/static/components/params_panel/components.js";


customElements.define("being-slider", Slider);
customElements.define("being-single-selection", SingleSelection);
customElements.define("being-multi-selection", MultiSelection);
customElements.define("being-motion-selection", MotionSelection);


function populate(container, obj, level=1) {
    for (const [key, param] of Object.entries(obj)) {
        if (typeof param !== "object") {
            console.log("Skipping", param);
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

                case "MotionSelection":
                    const mosel = document.createElement("being-motion-selection");
                    mosel.populate(param);
                    container.appendChild(mosel);
                    break

                default:
                    const paragraph = document.createElement('p');
                    paragraph.innerText = `Do not know what to do with ${param.blockType}`;
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

function init_parameters_elements(container, params) {
    populate(container, params, 1);
}


export class ParamsPanel extends Widget {
    constructor() {
        super();
        this._append_link("static/components/params_panel/params_panel.css");
        window.panel = this;
    }

    async connectedCallback() {
        const params = await get_json(API + "/params");
        init_parameters_elements(this.shadowRoot, params);
    }

    async content_changed() {
        const elements = this.shadowRoot.querySelectorAll("being-motion-selection")
        for (let motionSelection of elements) {
            const url = API + "/params/" + motionSelection.fullname;
            const params = await get_json(url);
            motionSelection.populate(params);
        }
    }
}
