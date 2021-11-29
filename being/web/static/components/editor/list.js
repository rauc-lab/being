/**
 * @module Spline / motion list for editor.
 */
import { Api } from "/static/js/api.js";
import { Curve } from "/static/js/curve.js";
import { make_editable } from "/static/js/editable_text.js";
import {
    assert, emit_custom_event, find_map_key_for_value, is_valid_filename,
    remove_all_children, rename_map_key,
} from "/static/js/utils.js";
import { WidgetBase } from "/static/js/widget.js";


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
export function as_curve(obj) {
    if (obj instanceof Curve) {
        return obj;
    }

    if (obj instanceof Object) {
        return Curve.from_dict(obj);
    }

    throw `Do not know what to do with ${obj}!`;
}


/**
 * Remove element from array.
 */
function remove_from_array(array, element) {
    const index = array.indexOf(element);
    if (index === -1) {
        throw `ValueError: remove_from_array(array, element): element not in array!`;
    }

    array.splice(index, 1);
}


const LIST_TEMPLATE = `
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

    ul li.in-focus {
        background: black;
        color: white;
    }

    /* visibility eye */

    ul li span.eye {
        margin-right: 0.5em;
        opacity: 0.0;
    }

    ul li span.eye.visible {
        opacity: 1.0;
    }

    ul li span.eye.hoverable:hover {
        opacity: 1.0;
    }

    /* other */

    ul li sup {
        margin-left: 0.25em;
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


export class List extends WidgetBase {
    constructor() {
        super();
        this.append_link("static/css/material_icons.css");
        this.append_template(LIST_TEMPLATE);
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
        });

        const curvesMsg = await this.api.get_curves();
        this.populate(curvesMsg.curves);

        const debug = false;
        if (debug) {
            this.addEventListener("contextmenu", evt => {
                console.log("DEBUG");
                console.log("selected", this.selected);
                console.log("curves", this.curves);
                console.log("associations", this.associations);
                console.log("armed", this.armed);
                evt.preventDefault();
            });
        }
    }

    // Private data accessors

    /**
     * Select curve. This also arms the curve.
     */
    select(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (name === this.selected) {
            return;
        }

        if (this.selected) {
            this.disarm(this.selected, false);
        }

        this.selected = name;
        this.arm(name, false);

        if (publish) {
            this.update_ui();
            this.emit_custom_event("selectedchanged");
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
            this.emit_custom_event("selectedchanged");
        }
    }

    /**
     * Associate curve with motion player.
     */
    associate_motion_player(name, motionPlayer) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        this.associations.set(name, motionPlayer.id);
        if (this.is_armed(name)) {
            const oldId = find_map_key_for_value(this.armed, name);
            rename_map_key(this.armed, oldId, motionPlayer.id);
        }
    }

    /**
     * Disassociate curve from motion player.
     */
    disassociate_motion_player(name) {
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

        const motionPlayers = Object.values(this.motionPlayers);
        if (motionPlayers.length === 0) {
            return undefined;
        }

        return motionPlayers[0];
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
        const mp = this.first_best_motion_player(name);
        if (mp !== undefined) {
            this.armed.set(mp.id, name);
        }

        if (publish) {
            this.update_ui();
            this.emit_custom_event("armedchanged");
        }
    }

    /**
     * Disarm curve.
     */
    disarm(name, publish=true) {
        assert(this.curves.has(name), `Unknown curve ${name}`);
        if (!this.is_armed(name)) {
            return console.log(name, "is not armed");
        }

        const mpId = find_map_key_for_value(this.armed, name);
        this.armed.delete(mpId);

        if (publish) {
            this.update_ui();
            this.emit_custom_event("armedchanged");
        }
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
        entry.eye.classList.add("eye");
        entry.eye.innerText = "visibility";

        entry.text = entry.appendChild(document.createElement("span"));
        entry.text.innerText = name;

        const sup = entry.appendChild(document.createElement("sup"));
        sup.innerText = curve.n_channels;

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
                this.emit_custom_event("selectedchanged");
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
            if (entry.name === this.selected) {
                return;
            }

            if (entry.eye.disabled) {
                return;
            }

            if (!this.associations.has(entry.name)) {
                return;
            }

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
     * Populate curve list with entries.
     */
    populate(namecurves) {
        remove_all_children(this.curveList);
        this.curves.clear();
        const names = [];

        // Create entries
        namecurves.forEach(namecurve => {
            let [name, curve] = namecurve;
            names.push(name);
            curve = as_curve(curve);
            this.add_entry(name, curve);
        });

        // Reset selected if necessary
        if (!this.curves.has(this.selected)) {
            this.selected = undefined;
        }

        // Remove outdated curves from armed
        for (const [key, value] of this.armed) {
            if (!names.includes(value)) {
                this.armed.delete(key);
            }
        }

        // Select next first best if any
        if (this.selected === undefined && namecurves.length > 0) {
            const firstName = namecurves[0][0];
            this.select(firstName);
        }

        this.update_ui();
    }

    /**
     * Emit a custom event for given event type from this element.
     */
    emit_custom_event(typeArg) {
        emit_custom_event(this, typeArg);
    }

    /**
     * Update UI from state.
     */
    update_ui() {
        const nothingSelected = (this.selected === undefined);
        this.deleteBtn.disabled = nothingSelected;
        this.duplicateBtn.disabled = nothingSelected;
        const hasMultipleMotionPlayers = Object.keys(this.motionPlayers).length > 1;

        for (let entry of this.curveList.childNodes) {
            if (entry.name === this.selected) {
                entry.classList.add('in-focus');
                entry.eye.disabled = true;
                entry.eye.classList.remove("visible");
                entry.eye.classList.remove("hoverable");
            } else if (this.is_armed(entry.name)) {
                entry.classList.remove('in-focus');
                entry.eye.disabled = true;
                entry.eye.classList.add("visible");
                entry.eye.classList.remove("hoverable");
            } else if (hasMultipleMotionPlayers) {
                entry.classList.remove('in-focus');
                entry.eye.disabled = false;
                entry.eye.classList.remove("visible");
                entry.eye.classList.add("hoverable");
            } else {
                entry.classList.remove('in-focus');
                entry.eye.disabled = true;
                entry.eye.classList.remove("visible");
                entry.eye.classList.remove("hoverable");
            }
        }
    }

    // Public

    /**
     * Get the currently selected curve (if any). undefined otherwise.
     */
    selected_curve() {
        return this.curves.get(this.selected);
    }

    /**
     * Process new content / motions message. Purge the currently displayed
     * curves.
     */
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

    /**
     * Get an array with all "background" curves. These are curves which are
     * armed but not the selected one.
     */
    background_curves() {
        const names = Array.from(this.armed.values());
        if (names.includes(this.selected)) {
            remove_from_array(names, this.selected);
        }

        const bgCurves = [];
        names.forEach((name) => {
            bgCurves.push(this.curves.get(name));
        });

        return bgCurves;
    }

    /**
     * Do we have an motion player association for a given curve?
     */
    has_association(name) {
        return this.associations.has(name);
    }
}

customElements.define("being-list", List);
