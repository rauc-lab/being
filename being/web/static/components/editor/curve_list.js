/**
 * @module Spline / motion list for editor.
 */
import { Api } from "/static/js/api.js";
import { BPoly } from "/static/js/spline.js";
import { WidgetBase } from "/static/js/widget.js";
import { create_button } from "/static/js/button.js";
import { make_editable } from "/static/js/editable_text.js";
import { remove_all_children, is_valid_filename, assert, rename_map_key, find_map_key_for_value, emit_event} from "/static/js/utils.js";


export class OldMotionList {
    constructor(editor) {
        this.editor = editor;
        this.splines = [];
        this.visibles = new Set();
        this.selected = null;
        this.api = new Api();

        this.init_elements();
    }

    /**
     * Load splines from back end and display in spline list.
     */
    async reload_spline_list() {
        const res = await this.api.fetch_splines();
        res.forEach(spline => {
            spline.content = BPoly.from_object(spline.content);
        });
        this.populate(res);
        this.editor.resize();
    }

    /**
     * Build node and attach to parent (editor)
     */
    init_elements() {
        const container = this.editor.motionListDiv;

        this.splineListDiv = document.createElement("div");
        //this.splineListDiv.style.borderBottom = "2px solid black";
        this.splineListDiv.style.paddingBottom = "5px";
        container.appendChild(this.splineListDiv);
        container.appendChild(document.createElement("hr"));

        const newBtnContainer = document.createElement("div");
        newBtnContainer.id = "spline-list-toolbar";
        container.appendChild(newBtnContainer);
        newBtnContainer.style.display = "flex";
        newBtnContainer.style.justifyContent = "center";

        const addSplineButton = create_button("add_box", "Create new spline");
        newBtnContainer.appendChild(addSplineButton);
        addSplineButton.addEventListener("click", async () => {
            this.editor.create_new_spline();
            this.reload_spline_list();
        });

        const delSplineButton = create_button("delete", "Delete selected motion");
        newBtnContainer.appendChild(delSplineButton);
        delSplineButton.addEventListener("click", () => {
            if (confirm("Delete motion " + this.selected + " permanently ?")) {
                this.api.delete_spline(this.selected).then(resp => {
                    if (resp.ok) {
                        this.visibles.delete(this.selected);
                        this.selected = null;
                        this.reload_spline_list();
                    }
                });
            }
        });

        const duplSplineButton = create_button("file_copy", "Duplicate motion file");
        newBtnContainer.appendChild(duplSplineButton);
        duplSplineButton.addEventListener("click", async () => {
            if (this.editor.confirm_unsaved_changes()) {
                const freename = await this.api.find_free_name(this.selected + " Copy");
                const spline = await this.api.get_spline(this.selected);
                await this.api.create_spline(freename, spline);
                this.selected = freename;
                this.reload_spline_list();
                this.editor.load_spline(spline);
            }
        });
    }

    update_spline_list() {
        remove_all_children(this.splineListDiv);

        this.splines.forEach(spline => {
            const entry = document.createElement("div");
            entry.classList.add("spline-list-entry");
            entry.classList.add("noselect");
            entry.id = spline.filename;
            entry.addEventListener("click", () => {
                if (!this.editor.confirm_unsaved_changes()) {
                    return;
                }

                if (entry.id !== this.selected) {
                    if (!this.preSelectVisibility) {
                        this.visibles.delete(this.selected);
                    }

                    this.selected = entry.id;
                    this.preSelectVisibility = this.visibles.has(this.selected);
                    // this.visibles.add(entry.id);
                    this.update_spline_list_selection();
                    this.draw_selected_spline();
                    const selectedSpline = this.splines.filter(sp => sp.filename === this.selected)[0];
                    this.editor.load_spline(selectedSpline.content);
                    this.draw_background_splines();
                }
            });

            const checkbox = document.createElement("span");
            checkbox.classList.add("spline-checkbox");
            checkbox.classList.add("material-icons");
            checkbox.classList.add("mdc-icon-button");
            checkbox.innerHTML = "";
            checkbox.value = spline.filename;
            checkbox.title = "Show in Graph";
            checkbox.addEventListener("click", evt => {
                evt.stopPropagation();
                const filename = evt.target.parentNode.id;
                if (this.selected === filename) {
                    this.preSelectVisibility = true;
                }

                if (this.visibles.has(filename)) {
                    this.visibles.delete(filename);
                } else {
                    this.visibles.add(filename);
                }

                this.update_spline_list_selection();
                this.draw_background_splines();
            }, true);
            checkbox.addEventListener("mouseover", evt => {
                evt.stopPropagation();
                checkbox.innerHTML = "visibility";
            });
            checkbox.addEventListener("mouseout", evt => {
                const filename = evt.target.parentNode.id;
                if (!this.visibles.has(filename)) {
                    checkbox.innerHTML = "";
                }
            });

            const text = document.createElement("span");
            text.innerHTML = spline.filename;
            text.contentEditable = "false";  // "false" prevents text syntax highlighting
            text.title = "Double click to edit";
            text.setAttribute("required", "");
            text.classList.add("truncate");
            entry.append(checkbox, text);
            text.addEventListener("blur", async evt => {
                text.contentEditable = "false";
                if (this.origFilename !== text.innerHTML) {
                    let newFilename = text.innerHTML;
                    if (newFilename.length <= 0 ||
                        newFilename === "<br>" ||
                        newFilename === "<p>" ||
                        newFilename === "<div>" ||
                        !is_valid_filename(newFilename)) {
                        text.innerHTML = this.origFilename;
                    } else {
                        const spline = await this.api.get_spline(this.origFilename);
                        newFilename = await this.api.find_free_name(newFilename)
                        await this.api.create_spline(newFilename, spline);
                        await this.api.delete_spline(this.origFilename)

                        let spl = this.splines.filter(sp => sp.filename === this.origFilename)[0];
                        spl.filename = newFilename;

                        if (this.selected === this.origFilename) {
                            this.selected = newFilename;
                        }

                        if (this.visibles.has(this.origFilename)) {
                            this.visibles.delete(this.origFilename);
                            this.visibles.add(newFilename);
                        }

                        const filename_div = this.editor.shadowRoot.getElementById(this.origFilename);
                        filename_div.id = newFilename;
                        text.innerHTML = newFilename;
                    }
                }

                text.classList.remove("nonvalid");
            });
            text.addEventListener("keyup", evt => {
                if (!is_valid_filename(evt.currentTarget.innerHTML)) {
                    text.classList.add("nonvalid");
                } else {
                    evt.currentTarget.classList.remove("nonvalid");
                }
                // Keyup eventListener needed to capture meta keys
                if (evt.key === "Escape") {
                    text.innerHTML = this.origFilename;
                    text.blur();  // saving file handled by "blur" eventListener
                }
            });
            text.addEventListener("dblclick", evt => {
                if (!text.isContentEditable) {
                    text.contentEditable = "true";
                    text.focus();
                    this.origFilename = text.innerHTML;
                }
            });
            text.addEventListener("keypress", evt => {
                // Keypress eventListener (compared to keyup) fires before contenteditable adds <br>
                if (evt.key === "Enter") {
                    text.blur();  // saving file handled by "blur" eventListener
                }
            });
            this.splineListDiv.append(entry);
        });
        this.update_spline_list_selection();
        this.draw_background_splines();
    }

    draw_background_splines() {
        this.editor.backgroundDrawer.clear();

        let background_splines = this.splines.filter(sp => {
            return (this.visibles.has(sp.filename) && sp.filename !== this.selected);
        });

        for (let index in background_splines) {
            const spline_to_draw = background_splines[index].content;
            this.editor.backgroundDrawer.draw_spline(spline_to_draw, false);
        }

        this.editor.backgroundDrawer.draw();
    }

    update_spline_list_selection() {
        const entries = this.editor.shadowRoot.querySelectorAll(".spline-list-entry");
        entries.forEach(entry => {
            entry.removeAttribute("checked");
            entry.querySelector(".spline-checkbox").innerHTML = "";
        });

        // Preselection 
        if (this.selected == null) {
            const latest = this.splines.length - 1;
            if (latest >= 0) {
                const spline_fd = this.splines[latest].filename;
                this.selected = spline_fd;
                this.preSelectVisibility = false;
            }
            this.draw_selected_spline();
        }

        if (this.selected !== null) {
            this.editor.shadowRoot.getElementById(this.selected).setAttribute("checked", "");
            this.visibles.forEach(filename => {
                const parent = this.editor.shadowRoot.getElementById(filename);
                const checkbox = parent.querySelector(".spline-checkbox");
                checkbox.innerHTML = "visibility";
            });
        }
    }

    /**
     * Draw the currently selected spline in editor panel (if any).
     */
    draw_selected_spline() {
        for (const sp of this.splines) {
            if (sp.filename === this.selected) {
                this.editor.load_spline(sp.content);
                break;
            }
        }
    }

    /**
     * Populate spline list with splines.
     *
     * @param {Array} splines Array of spline like objects (filename and content).
     */
    populate(splines) {
        this.splines = splines;
        this.update_spline_list();
    }
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


function map_setdefault(map, key, defaultValue) {
    if (!map.has(key)) {
        map.set(key, defaultValue);
    }
    return map.get(key)
}


function is_empty_object(obj) {
    // because Object.keys(new Date()).length === 0;
    // we have to do some additional check
    return obj // 👈 null and undefined check
        && Object.keys(obj).length === 0
        && Object.getPrototypeOf(obj) === Object.prototype;
}


export class CurveList extends WidgetBase {
    constructor() {
        super();
        this._append_link("static/css/material_icons.css");
        this.append_template(CURVE_LIST_TEMPLATE);
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

    selected_curve() {
        return this.curves.get(this.selected);
    }

    armed_curves() {
        return this.armed.values();
    }

    background_curves() {
        const names = Array.from(this.armed.values());
        names.pop(this.selected);
    }

    populate(namecurves) {
        this.clear();

        namecurves.forEach(namecurve => {
            const [name, curve] = namecurve;
            this.add_entry(name, curve);
        });

        if (namecurves.length > 0) {
            const firstName = namecurves[0][0];
            this.select(firstName);
        }
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
        const curvesMsg = await api.get_curves();
        this.populate(curvesMsg.curves);
        return
        this.addEventListener("contextmenu", evt => {
            // Debug infos
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

customElements.define("being-curve-list", CurveList);
