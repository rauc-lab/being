import { Widget } from "/static/js/widget.js";
import { Api } from "/static/js/api.js";
import { remove_all_children } from "/static/js/utils.js";
import { round } from "/static/js/math.js";


/** Maximum attnetion span in seconds */
const MAX_ATTENTION_SPAN = 30.;

const N_TICKS = 1000;

/**
 * Pluck motion names from spline list.
 *
 * @param {Array} splines Spline motions.
 * @returns Array of motion names.
 */
function pluck_motion_names(splines) {
    const names = [];
    splines.forEach(obj => {
        names.push(obj.filename);
    });

    return names;
}


class Behavior extends Widget {
    constructor() {
        console.log("Behavior.constructor()");
        super();
        this.api = new Api();
        this.attentionSpanSlider = null;
        this.nowPlayingSpan = null;
        this.statesDiv = null;
        this.attentionSpanSpan = null;
    }

    connectedCallback() {
        console.log("Behavior.connectedCallback()");
        this.add_button_to_toolbar("play_arrow");
        this.init_elements();
        this.init_ui();
    }

    init_elements() {
        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/behavior.css");
        this.shadowRoot.appendChild(link);

        const container = document.createElement("div");
        container.classList.add("container");
        this.shadowRoot.appendChild(container);

        // Attention span
        const label = document.createElement("label");
        container.appendChild(label);
        container.setAttribute("for", "attentionSpan");
        label.innerHTML = "Attention Span:";

        const slider = document.createElement("input");
        container.appendChild(slider);
        slider.setAttribute("type", "range");
        slider.setAttribute("name", "attentionSpan");
        slider.setAttribute("min", 0);
        slider.setAttribute("max", N_TICKS);
        this.attentionSpanSlider = slider;

        const span = document.createElement("span");
        container.appendChild(span);
        span.update = evt => {
            const seconds = slider.value / N_TICKS * MAX_ATTENTION_SPAN;
            span.innerHTML = round(seconds, 1) + " sec";
        };
        slider.addEventListener("input", span.update);
        span.update();
        this.attentionSpanSpan = span;

        // States
        container.appendChild(document.createElement("br"));

        const nowPlayingLabel = document.createElement("label");
        container.appendChild(nowPlayingLabel);
        nowPlayingLabel.innerHTML = "Now playing: ";

        const nowPlayingSpan = document.createElement("span");
        container.appendChild(nowPlayingSpan);
        nowPlayingSpan.classList.add("now-playing");
        nowPlayingSpan.innerHTML = "";
        this.nowPlayingSpan = nowPlayingSpan;

        const statesDiv = document.createElement("div");
        container.appendChild(statesDiv);
        statesDiv.classList.add("states");
        this.statesDiv = statesDiv;
    }

    async init_ui() {
        const stateNames = await this.api.fetch_behavior_states();
        this.populate_states(stateNames);

        const splines = await this.api.fetch_splines();
        const names = pluck_motion_names(splines);
        this.populate_motions(names);

        const params = await this.api.get_behavior_params();
        this.update_ui(params);
    }

    update_ui(params) {
        console.log("params:", params);
        const value = params.attentionSpan / MAX_ATTENTION_SPAN * N_TICKS;
        this.attentionSpanSlider.value = value;
        this.attentionSpanSpan.update();
        this.statesDiv.childNodes.forEach(stateDiv => {
            const key = stateDiv.getAttribute("name").toLowerCase() + "Motions";
            const motions = params[key];
            stateDiv.querySelectorAll("input[type='checkbox']").forEach(cb => {
                cb.checked = motions.includes(cb.name);
            });
        });
    }



    /**
     * Populate box for each state.
     *
     * @param {Array} stateNames Array of state names.
     */
    populate_states(stateNames) {
        remove_all_children(this.statesDiv);
        stateNames.forEach(name => {
            const stateDiv = document.createElement("div");
            stateDiv.setAttribute("name", name);
            this.statesDiv.appendChild(stateDiv);
            stateDiv.classList.add("state");

            const span = document.createElement("span");
            span.innerHTML = name;
            stateDiv.appendChild(span);

            const ul = document.createElement("ul");
            stateDiv.appendChild(ul);
        });
    }

    populate_motions(motions) {
        // Number prefix for input id in order to distinguish between the same motion between the different states
        let counter = 0;
        this.statesDiv.querySelectorAll("ul").forEach(ul => {
            remove_all_children(ul);
            motions.forEach(motion => {
                const id = counter + motion;
                counter += 1;

                const li = document.createElement("li");
                ul.appendChild(li);

                const cb = document.createElement("input");
                li.appendChild(cb);
                cb.setAttribute("type", "checkbox");
                cb.setAttribute("id", id);
                cb.setAttribute("name", motion);
                cb.hidden = true;
                cb.addEventListener("input", evt => {
                    this.emit();
                });

                const label = document.createElement("label");
                li.appendChild(label);
                label.setAttribute("for", id);
                label.innerHTML = motion;
            });
        });
    }

    emit() {
        const params = {};
        params.attentionSpan = this.attentionSpanSlider.value / N_TICKS;
        this.statesDiv.childNodes.forEach(stateDiv => {
            const key = stateDiv.getAttribute("name").toLowerCase() + "Motions";
            params[key] = [];
            stateDiv.querySelectorAll("input[type='checkbox']:checked").forEach(cb => {
                params[key].push(cb.name);
            });
        });
        this.api.send_behavior_params(params);
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

    new_data(msg) {
        if (msg.type === "behavior-update") {
            this.nowPlayingSpan.innerHTML = msg.lastPlayed;
            this.mark_active_state(msg.state.value);
        }
    }
}

customElements.define("being-behavior", Behavior);