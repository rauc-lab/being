/**
 * @module Spline / motion list for editor.
 */
import { Api } from "/static/js/api.js";
import { BPoly } from "/static/js/spline.js";
import { WidgetBase } from "/static/js/widget.js";
import { make_editable } from "/static/js/editable_text.js";
import {
    assert, emit_event, find_map_key_for_value, is_valid_filename,
    remove_all_children, rename_map_key,
} from "/static/js/utils.js";


/**
 * Get first map key (if any). undefined otherwise.
 */
function first_map_key(map) {
    if (map.size > 0) {
        const [key, value] = map.entries().next().value;
        return key;
    }
}


/**
 * Assure bpoly object.
 */
function as_bpoly(obj) {
    if (obj instanceof BPoly) {
        return obj;
    }

    if (obj instanceof Object) {
        return BPoly.from_object(obj);
    }

    throw `Do not know what to do with ${obj}!`;
}


const CURVE_LIST_TEMPLATE = `
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


export class CurveList extends WidgetBase {
    constructor() {
        super();
        this._append_link("static/css/material_icons.css");
        this.append_template(CURVE_LIST_TEMPLATE);
        this.api = new Api();
        this.motionPlayers = {};

        // Relevant HTML elements
        this.curveList = this.shadowRoot.getElementById("curve-list");
        this.newBtn = this.shadowRoot.getElementById("new-button");
        this.deleteBtn = this.shadowRoot.getElementById("delete-button");
        this.duplicateBtn = this.shadowRoot.getElementById("duplicate-button");

        // Mutable / changeable states
        this.selected = undefined;  // Currently selected curve name
        this.curves = new Map();  // All curves. Curve name -> curve
        this.associations = new Map();  // Motion player associations. Curve name -> Motion player ID
        this.armed = new Map();  // Currently armed curves. Motion player id -> Curve name
    }

    // Private

    async connectedCallback() {
        this.motionPlayers = {};
        const motionPlayers = await this.api.get_motion_player_infos();
        motionPlayers.forEach(mp => {
            this.motionPlayers[mp.id] = mp;
        })

        const curvesMsg = await this.api.get_curves();
        this.populate(curvesMsg.curves);
    }

    // Private data accessors

    /**
     * Select curve. This also arms the curve.
     */
    select(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (name === this.selected) {
            return console.log(name, "is allready selected");
        }

        if (this.selected) {
            this.disarm(this.selected, false);
        }

        this.selected = name;
        this.arm(name, false);

        if (publish) {
            this.update_ui();
            emit_event(this, "change");
        }
    }

    /**
     * Deselect curve. This also disarms the curve.
     */
    deselect(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        this.disarm(this.selected, false);
        this.selected = undefined;

        if (publish) {
            this.update_ui();
            emit_event(this, "change");
        }
    }

    /**
     * Associate curve with motion player.
     */
    associate_motion_player(name, motionPlayer) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        this.associations.set(name, motionPlayer.id);
    }

    /**
     * Disassociate curve from motion player.
     */
    disassociate_motion_player(name, motionPlayer) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        this.associations.delete(name);
    }

    /**
     * Get associated motion player for curve (if any).
     */
    associated_motion_player(name) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (!this.associations.has(name)) {
            return;
        }
        const id = this.associations.get(name);
        return this.motionPlayers[id];
    }

    /**
     * Get first best match for curve. Associated or the first known motion
     * player.
     */
    first_best_motion_player(name) {
        if (this.associations.has(name)) {
            const id = this.associations.get(name);
            return this.motionPlayers[id];
        }

        return Object.values(this.motionPlayers)[0]
    }

    /**
     * Check if curve is armed.
     */
    is_armed(name) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        return Array.from(this.armed.values()).includes(name);
    }

    /**
     * Arm curve.
     */
    arm(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (this.is_armed(name)) {
            return console.log(name, "is allready armed");
        }

        const mp = this.first_best_motion_player(name);
        this.armed.set(mp.id, name);

        if (publish) {
            this.update_ui();
            emit_event(this, "change");
        }
    }

    /**
     * Disarm curve.
     */
    disarm(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (!this.is_armed(name)) {
            return console.log(name, "is allready disarmed");
        }

        const mpId = find_map_key_for_value(this.armed, name);
        this.armed.delete(mpId);
        this.update_ui();
    }

    // Private misc

    /**
     * Filename validator. Trims white space and checks validity for filename
     * usage. Throws error otherwise. Compatible with make_editable() function.
     */
    validate_name(name) {
        name = name.trim();
        if (is_valid_filename(name) && !this.curves.has(name)) {
            return name;
        }

        throw `"${name}" is an invalid name!`;
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

    /**
     * Rename curve in curve list data.
     */
    async rename_curve(oldName, newName) {
        const curve = await this.api.get_curve(oldName);
        this.deselect(oldName, false);
        rename_map_key(this.curves, oldName, newName);
        rename_map_key(this.associations, oldName, newName);
        this.select(newName, false);
        await this.api.rename_curve(oldName, newName);
    }

    /**
     * Attache necessary event listeners to list entry.
     * - Clicking for select
     * - Toggle eye symbol for arming
     * - Double clicking for renaming.
     */
    attache_event_listeners_to_entry(entry) {
        assert(entry.hasOwnProperty("name"), "entry has no name attribute!");

        make_editable(
            entry.text,
            async newName => {
                const oldName = entry.name;
                const freename = await this.api.find_free_name(newName);
                await this.rename_curve(oldName, freename)
                entry.name = freename;
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

    /**
     * Add new curve entry to list.
     */
    add_entry(name, curve) {
        const entry = this.create_entry(name, curve);
        this.curveList.appendChild(entry);
        this.curves.set(name, curve);
    }

    /**
     * Update UI from state.
     */
    update_ui() {
        const nothingSelected = (this.selected === undefined);
        this.deleteBtn.disabled = nothingSelected;
        this.duplicateBtn.disabled = nothingSelected;

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

    /**
     * Populate curve list with entries.
     */
    populate(namecurves) {
        remove_all_children(this.curveList);
        this.curves.clear();
        namecurves.forEach(namecurve => {
            let [name, curve] = namecurve;
            curve = as_bpoly(curve);
            this.add_entry(name, curve);
        });

        if (!this.curves.has(this.selected)) {
            this.selected = undefined;
        }

        if (this.selected === undefined && namecurves.length > 0) {
            const firstName = namecurves[0][0];
            this.select(firstName);
        }

        this.update_ui();
    }

    // Public

    selected_curve() {
        return this.curves.get(this.selected);
    }

    //armed_curves() {
    //    return this.armed.values();
    //}

    //background_curves() {
    //    const names = Array.from(this.armed.values());
    //    names.pop(this.selected);
    //}

    new_motions_message(msg) {
        const wasSelected = this.selected;
        this.populate(msg.curves);

        if (this.curves.size === 0) {
            return
        }
        const doesNotExistAnymore = !this.curves.has(wasSelected);
        if (doesNotExistAnymore) {
            const firstName = first_map_key(this.curves);
            this.select(firstName);
        } else {
            this.select(wasSelected);
        }
    }
}

customElements.define("being-curve-list", CurveList);
