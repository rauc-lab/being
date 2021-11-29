import { Slider, SingleSelection, MultiSelection, MotionSelection } from "/static/components/params_panel/components.js";  // Needs to be imported in order to register custom elements
import { API } from "/static/js/config.js";
import { get_json } from "/static/js/fetching.js";
import { Widget } from "/static/js/widget.js";


function populate(container, obj, level=1) {
    for (const [key, param] of Object.entries(obj)) {
        if (typeof param !== "object") {
            console.log("Skipping", param);
            continue;
        }

        if (param.type === "Block") {
            let widget = document.createElement('p');
            widget.innerText = `Do not know what to do with ${param.blockType}`;
            switch (param.blockType) {
                case "Slider":
                    widget = document.createElement("being-slider");
                    widget.populate(param);
                    break;

                case "SingleSelection":
                    widget = document.createElement("being-single-selection");
                    widget.populate(param);
                    break

                case "MultiSelection":
                    widget = document.createElement("being-multi-selection");
                    widget.populate(param);
                    break

                case "MotionSelection":
                    widget = document.createElement("being-motion-selection");
                    widget.populate(param);
                    break
            }

            container.appendChild(widget);
        } else {
            const heading = document.createElement("h" + level);
            heading.innerText = key;
            container.appendChild(heading);
            populate(container, param, level + 1);
        }
    }
}

function init_parameters_elements(container, params) {
    populate(container, params, 2);
}


export class ParamsPanel extends Widget {
    constructor() {
        super();
        this.append_link("static/components/params_panel/params_panel.css");
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


customElements.define("being-params-panel", ParamsPanel);