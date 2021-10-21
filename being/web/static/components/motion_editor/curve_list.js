import { Api } from "/static/js/api.js";
import { BPoly } from "/static/js/spline.js";
import { create_button } from "/static/js/button.js";
import { remove_all_children, is_valid_filename, assert, rename_map_key, find_map_key_for_value} from "/static/js/utils.js";
import { append_link_to, append_template_to } from "/static/js/widget.js";
import { make_editable } from "/static/js/editable_text.js";


const TEMPLATE = `
<style>
    :host {
        border-right: 2px solid black;
        min-width: 200px;
    }

    ul {
        list-style-type: none;
        margin: 0;
        padding: 0;
    }

    ul li {
        cursor: pointer;
        padding: 0.75em;
        display: flex;
    }

    ul li sup {
        margin-left: 0.25em;
    }

    ul li.in-focus {
        background: black;
        color: white;
    }

    ul span:first-child {
        margin-right: 0.5em;
    }

    ul span:first-child.opaque {
        opacity: 0.0;
    }

    ul span:first-child:hover {
        opacity: 1.0;
    }

    hr {
        border: 1px solid black;
        margin: 2px;
        margin-bottom: 0.5em;
    }

    div.footer-toolbar {
        display: flex;
        justify-content: center;
    }

    div.footer-toolbar button {
        border: none;
        background: none;
        cursor: pointer;
    }
</style>

<ul id="curve-list"></ul>
<hr>
<div class="footer-toolbar">
    <button id="new-button" class="material-icons" title="Create new spline">add_box</button>
    <button id="delete-button" class="material-icons" title="Delete selected motion">delete</button>
    <button id="duplicate-button" class="material-icons" title="Duplicate motion file">file_copy</button>
</div>
`;


function map_setdefault(map, key, defaultValue) {
    if (!map.has(key)) {
        map.set(key, defaultValue);
    }
    return map.get(key)
}


/**
 * Emit event for HTML element.
 */
function emit_event(ele, type, bubbles=true, cancelable=true) {
    if ("createEvent" in document) {
        const evt = document.createEvent("HTMLEvents");
        evt.initEvent(type, bubbles, cancelable);
        evt.eventName = type;
        ele.dispatchEvent(evt);
    } else {
        const evt = document.createEventObject();
        evt.eventName = type;
        evt.eventType = type;
        ele.fireEvent("on" + evt.eventType, evt);
    }
}


export class CurveList extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        append_link_to("static/css/material_icons.css", this.shadowRoot);
        append_template_to(TEMPLATE, this.shadowRoot);
        this.curveList = this.shadowRoot.getElementById("curve-list");
        this.newBtn = this.shadowRoot.getElementById("new-button");
        this.deleteBtn = this.shadowRoot.getElementById("delete-button");
        this.duplicateBtn = this.shadowRoot.getElementById("duplicate-button");
        this.motionPlayers = [];

        // Mutable / changeable attributes
        this.curves = new Map();  // Curve name: str -> Curve: BPoly
        this.selected = null;  // Curve name: str
        this.associatedMotionPlayers = new Map();  // Curve name: str -> Motion player
        this.armed = new Map();  // Motion player -> Curve name: str
    }

    // Public
    //get selected_curve() { return this.curves.get(this.selected); }

    populate(curves) {
        console.log("CurveList.populate()");
        this.clear();
        for (const [name, obj] of Object.entries(curves)) {
            const curve = BPoly.from_object(obj);
            this.add_entry(name, curve);
        }

        const firstName = this.curves.keys().next().value;
        this.select(firstName);
    }

    associate_motion_player_with_current_curve(mp) {
        console.log("CurveList.associate_motion_player_with_current_curve()", mp);
        //if (this.selected === null) { return; }
        console.log("  selected:", this.selected);
        this.associatedMotionPlayers.set(this.selected, mp);
        if (this.is_armed(this.selected)) {
            this.arm(this.selected);
        }
    }

    associated_motion_player() {
        return this.which_motion_player_for_curve(this.selected);
    }

    // Private

    async connectedCallback() {
        const api = new Api();
        this.motionPlayers = await api.get_motion_player_infos();
        const allMotions = await api.load_motions();
        this.populate(allMotions.splines);
        this.addEventListener("contextmenu", evt => {
            evt.preventDefault();
            console.log("CurveList current state:");
            //console.log("  curves:", this.curves);
            console.log("  selected:", this.selected);
            //console.log("  associatedMotionPlayers:", this.associatedMotionPlayers);
            console.log("  associatedMotionPlayers:");
            for (const [name, mp] of this.associatedMotionPlayers) {
                console.log("    ", name, "->", mp);
            }
            //console.log("  armed:", this.armed);
        });
    }

    clear() {
        //this.motionPlayers = [];
        remove_all_children(this.curveList);
        this.curves = new Map();
        this.selected = null;
    }

    is_armed(name) {
        return Array.from(this.armed.values()).includes(name);
    }

    which_motion_player_for_curve(name) {
        if (!this.associatedMotionPlayers.has(name)) {
            const curve = this.curves.get(name);
            let candidate = this.motionPlayers.find(mp => mp.ndim === curve.ndim);
            if (candidate !== undefined) {
                candidate = this.motionPlayers[0];
            }
            this.associatedMotionPlayers.set(name, candidate);
        }

        return this.associatedMotionPlayers.get(name);
    }

    validate_name(name) {
        name = name.trim();
        if (is_valid_filename(name) && !this.curves.has(name)) {
            return name;
        }

        throw `"${name}" is an invalid name!`;
    }

    /**
     * Add new curve entry to list.
     */
    add_entry(name, curve) {
        const entry = this.create_entry(name, curve);
        this.curveList.appendChild(entry);
        this.curves.set(name, curve);
    }

    /**
     * Create new list curve entry.
     */
    create_entry(name, curve) {
        const entry = document.createElement("li");
        entry.name = name;

        entry.eye = entry.appendChild(document.createElement("span"));
        entry.eye.classList.add("material-icons");
        entry.eye.classList.add("mdc-icon-button");
        entry.eye.classList.add("opaque");
        entry.eye.innerText = "visibility";

        entry.text = entry.appendChild(document.createElement("span"));
        entry.text.innerText = name;

        const sup = entry.appendChild(document.createElement("sup"));
        sup.innerText = curve.ndim;

        this.attache_event_listeners_to_entry(entry);
        return entry;
    }

    attache_event_listeners_to_entry(entry) {
        assert(entry.hasOwnProperty("name"), "entry has no name attribute!");

        make_editable(
            entry.text,
            newName => {
                // Rename entry
                const oldName = entry.name;

                rename_map_key(this.curves, oldName, newName);

                if (this.selected === oldName) {
                    this.selected = newName;
                }

                rename_map_key(this.associatedMotionPlayers, oldName, newName);

                if (this.is_armed(oldName)) {
                    const mp = find_map_key_for_value(this.armed, oldName);
                    this.armed.set(mp, newName);
                }

                entry.name = newName;
            },
            newName => {
                // Validate new name
                return this.validate_name(newName);
            }
        );

        entry.addEventListener("click", () => {
            this.select(entry.name);
        });

        entry.eye.addEventListener("click", evt => {
            if (this.is_armed(entry.name)) {
                this.disarm(entry.name);
            } else {
                this.arm(entry.name);
            }
            evt.stopPropagation();
        });
    }

    select(name) {
        console.log("CurveList.select()", name);
        if (name === this.selected) {
            console.log(name, "is allready selected");
            return
        }

        if (this.selected !== null) {
            this.disarm(this.selected);
        }

        this.selected = name;
        this.arm(name);  // Triggers update_ui()
        emit_event(this, "change");
    }

    arm(name) {
        console.log("CurveList.arm()", name);
        const mp = this.which_motion_player_for_curve(name)
        this.armed.set(mp, name);
        this.update_ui();
        emit_event(this, "change");
    }

    disarm(name) {
        console.log("CurveList.disarm()", name);
        if (this.is_armed(name)) {
            const mp = find_map_key_for_value(this.armed, name);
            this.armed.delete(mp);
            this.update_ui();
        }
    }

    update_ui() {
        console.log('CurveList.update_ui()');
        for (let entry of this.curveList.childNodes) {
            if (entry.name === this.selected) {
                entry.classList.add('in-focus');
            } else {
                entry.classList.remove('in-focus');
            }

            if (this.is_armed(entry.name) && entry.name !== this.selected) {
                entry.eye.classList.remove('opaque');
            } else {
                entry.eye.classList.add('opaque');
            }
        }
    }
    
}


customElements.define('being-curve-list', CurveList);
