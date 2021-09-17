import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";
import { clip } from "/static/js/math.js";
import { Widget } from "/static/js/widget.js";
import { remove_all_children, clear_array } from "/static/js/utils.js";
import { init_parameters_elements } from "/static/components/control_panel/parameters.js";


export class ParamsPanel extends Widget {
    constructor() {
        console.log("BeingParamsPanel.constructor()");
        super();
    }

    connectedCallback() {
        console.log("BeingParamsPanel.connectedCallback()");
        const params = await get_json("/api/params");
        init_parameters_elements(this.shadowRoot, params);
    }
}