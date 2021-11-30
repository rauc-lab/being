/**
 * @module behavior Behavior web component widget.
 *
 * The HTML <being-behavior> widget needs to know its behavior id, so that we
 * can map the API requests correctly (via an instance of BehaviorApi).
 */
import { API } from "/static/js/config.js";
import { Api } from "/static/js/api.js";
import { Widget } from "/static/js/widget.js";
import { get_json, put_json} from "/static/js/fetching.js";
import { remove_all_children } from "/static/js/utils.js";
import { round } from "/static/js/math.js";


/** Maximum attnetion span in seconds */
const MAX_ATTENTION_SPAN = 30.;

/** Number of tick of attention span slider. */
const N_TICKS = 1000;

/** @const {HTMLElement} - Main template for behavior widget. */
const BEHAVIOR_TEMPLATE = `
<div class="container">
    <div id="statesDiv" class="states"></div>
</div>
`;


class BehaviorApi extends Api {
    constructor(id) {
        super();
        this.id = id;
    }

    async load_behavior() {
        return get_json(API + "/behaviors/" + this.id);
    }

    async load_behavior_states() {
        return get_json(API + "/behaviors/" + this.id + "/states");
    }

    async toggle_behavior_playback() {
        return put_json(API + "/behaviors/" + this.id + "/toggle_playback");
    }

    async send_behavior_params(params) {
        return put_json(API + "/behaviors/" + this.id + "/params", params);
    }
}


export class Behavior extends Widget {
    constructor() {
        super();
        this.api = null;
        this.attentionSpanSlider = null;
        this.attentionSpanSpan = null;
        this.led = null;
        this.nowPlayingSpan = null;
        this.statesDiv = null;

        this.init_html_elements();
    }

    /**
     * Get behavior id for this widget from "behaviorId" HTML attribute as int.
     * Return -1 if not set.
     */
    get id() {
        const attr = this.getAttribute("behaviorId");
        if (attr === null) {
            return -1;
        }

        return parseInt(attr);
    }

    async connectedCallback() {
        this.api = new BehaviorApi(this.id);
        this.load();
    }

    /**
     * Build DOM elements.
     */
    init_html_elements() {
        this.playPauseBtn = this.add_button_to_toolbar("play_arrow");
        this.append_link("static/components/behavior/behavior.css");
        this.append_template(BEHAVIOR_TEMPLATE);

        this.statesDiv = this.shadowRoot.getElementById("statesDiv");

        const label = document.createElement("label");
        this.toolbar.appendChild(label);
        label.innerHTML = "Now playing: ";
        label.style.marginLeft = "0.5em";
        label.style.marginRight = "0.5em";
        this.nowPlayingSpan = document.createElement("span");
        this.nowPlayingSpan.classList.add("now-playing");
        this.toolbar.appendChild(this.nowPlayingSpan);
        this.attentionSpanSlider = document.createElement("input");
        this.attentionSpanSlider.setAttribute("type", "range");
        this.attentionSpanSlider.setAttribute("min", 0);
        this.attentionSpanSlider.setAttribute("max", N_TICKS);
        this.attentionSpanSlider.setAttribute("name", "attentionSpan");
        this.attentionSpanSpan = document.createElement("span");
        this.attentionSpanSpan.style = "display: inline-block; min-width: 3.5em; text-align: right;";
        this.led = document.createElement("span");
        this.led.classList.add("led");
    }

    /**
     * Load behavior state / params from server and populate HTML elements.
     */
    async load() {
        const stateNames = await this.api.load_behavior_states();
        this.populate_states(stateNames);

        const content = await this.api.get_curves();
        const names = content.curves.map(curvename => {return curvename[0]});
        this.populate_motions(names);

        const behavior = await this.api.load_behavior();
        this.update(behavior);

        this.playPauseBtn.addEventListener("click", async () => {
            const behavior = await this.api.toggle_behavior_playback();
            this.update(behavior);
        });
        this.attentionSpanSlider.addEventListener("change", () => {
            this.emit_params();
        });
        this.attentionSpanSlider.addEventListener("input", () => {
            const duration = this.attentionSpanSlider.value * MAX_ATTENTION_SPAN / N_TICKS;
            this.update_attention_span_label(duration);
        });

    }

    /**
     * Populate box for each state.
     *
     * @param {Array} stateNames Array of state names.
     */
    populate_states(stateNames) {
        remove_all_children(this.statesDiv);
        stateNames.forEach((name, nr) => {
            const stateDiv = document.createElement("div");
            stateDiv.setAttribute("name", name);
            this.statesDiv.appendChild(stateDiv);
            stateDiv.classList.add("state");

            // State name / title
            const stateNameDiv = document.createElement("span");
            stateDiv.appendChild(stateNameDiv);
            stateNameDiv.classList.add("title");
            stateNameDiv.innerHTML = name;

            // State specific infos / params
            const div = document.createElement("span");
            div.classList.add("infos");
            stateDiv.appendChild(div);

            switch(nr) {
                case 0:
                    div.append("Default Fallback");
                    break;
                case 1:
                    div.append("Min. Duration:");
                    div.appendChild(this.attentionSpanSlider);
                    div.appendChild(this.attentionSpanSpan);
                    break;
                case 2:
                    div.append("Triggered:");
                    div.appendChild(this.led);
                    break;
                default:
            }

            // Init motion list
            const ul = document.createElement("ul");
            stateDiv.appendChild(ul);
        });
    }

    /**
     * Update motion name lists.
     *
     * @param {Array} names Motion names.
     */
    populate_motions(names) {
        /** Counter for id number prefix in order to distinguish between the
         * same motion between the different states */
        let counter = 0;
        this.statesDiv.querySelectorAll("ul").forEach(ul => {
            remove_all_children(ul);
            names.forEach(name => {
                const id = counter + name;
                counter += 1;

                const li = document.createElement("li");
                ul.appendChild(li);

                const cb = document.createElement("input");
                li.appendChild(cb);
                cb.setAttribute("type", "checkbox");
                cb.setAttribute("id", id);
                cb.setAttribute("name", name);
                cb.hidden = true;
                cb.addEventListener("input", () => {
                    this.emit_params();
                });

                const label = document.createElement("label");
                li.appendChild(label);
                label.setAttribute("for", id);
                label.innerHTML = name;
            });
        });
    }

    /**
     * Mark active state.
     *
     * @param {Number} nr State number (enum value).
     */
    mark_active_state(nr) {
        this.statesDiv.childNodes.forEach((child, i) => {
            if (i === nr) {
                child.classList.add("selected");
            } else {
                child.classList.remove("selected");
            }
        });
    }

    update_attention_span_label(duration) {
        this.attentionSpanSpan.innerHTML = round(duration, 1) + " sec";
    }

    /**
     * Update attention span elements.
     *
     * @param {Number} duration Attention span time duration in seconds.
     */
    update_attention_span_slider(duration) {
        const value = duration / MAX_ATTENTION_SPAN * N_TICKS;
        this.attentionSpanSlider.value = value;
    }

    /**
     * Trigger LED pulse animation for one cycle.
     */
    pulse_led() {
        // Retrigger CSS animation. We need to void access offsetWidth for it
        // to work (?!). See section "Update: Another JavaScript Method to
        // Restart a CSS Animation" at
        // https://css-tricks.com/restart-css-animation/
        this.led.classList.remove("pulsing");
        this.led.offsetWidth;
        this.led.classList.add("pulsing");
    }

    /**
     * Update all UI elements from a behavior message.
     *
     * @param {Object} behavior Behavior info object.
     */
    update(behavior) {
        if (behavior.id !== this.id) {
            console.log("Skipping behavior. Wrong id", behavior.id, "for this widget (id", this.id + ")!");
            return;
        }

        this.playPauseBtn.change_icon(behavior.active ? "pause" : "play_arrow");
        this.nowPlayingSpan.innerHTML = behavior.lastPlayed;
        this.update_attention_span_slider(behavior.params.attentionSpan);
        this.update_attention_span_label(behavior.params.attentionSpan);
        this.statesDiv.childNodes.forEach((stateDiv, nr) => {
            const names = behavior.params.motions[nr];
            const ul = stateDiv.querySelector("ul");
            ul.querySelectorAll("input[type='checkbox']").forEach(cb => {
                cb.checked = names.includes(cb.name);
            });
            ul.querySelectorAll("label").forEach(label => {
                if (label.innerHTML === behavior.lastPlayed) {
                    label.classList.add("now-playing-motion");
                } else {
                    label.classList.remove("now-playing-motion");
                }
            });
        });
        this.mark_active_state(behavior.active ? behavior.state.value : -1);
    }

    /**
     * Emit current behavior params to back end.
     */
    async emit_params() {
        const params = {};
        params.attentionSpan = this.attentionSpanSlider.value / N_TICKS * MAX_ATTENTION_SPAN;
        params.motions = [];
        this.statesDiv.childNodes.forEach((stateDiv, nr) => {
            const selected = [];
            stateDiv.querySelectorAll("input[type='checkbox']:checked").forEach(cb => {
                selected.push(cb.name);
            });
            params.motions.push(selected);
        });
        const behavior = await this.api.send_behavior_params(params);
        this.update(behavior);
    }

    /**
     * New behavior message callback for web socket.
     *
     * @param {Object} msg Received message to process.
     */
    async new_behavior_message(msg) {
        this.update(msg.behavior);
    }

    /**
     * New content changed message callback for web socket.
     *
     * @param {Object} msg ?
     */
    async content_message(msg) {
        const names = msg.curves.map(curvename => curvename[0]);
        this.populate_motions(names);
        const behavior = await this.api.load_behavior();
        this.update(behavior);
    }
}

customElements.define("being-behavior", Behavior);
