/**
 * @module behavior Behavior web component widget.
 */
import { Widget } from "/static/js/widget.js";
import { Api } from "/static/js/api.js";
import { remove_all_children } from "/static/js/utils.js";
import { round } from "/static/js/math.js";


/** Maximum attnetion span in seconds */
const MAX_ATTENTION_SPAN = 30.;

/** Number of tick of attention span slider. */
const N_TICKS = 1000;


class Behavior extends Widget {
    constructor() {
        super();
        this.api = new Api();
        this.attentionSpanSlider = null;
        this.nowPlayingSpan = null;
        this.statesDiv = null;
        this.attentionSpanSpan = null;
    }

    connectedCallback() {
        this.init_elements();
        this.load();
    }

    async load() {
        const stateNames = await this.api.load_behavior_states();
        this.populate_states(stateNames);

        const motions = await this.api.load_motions();
        const names = Object.keys(motions.splines);
        this.populate_motions(names);

        const infos = await this.api.load_behavior_infos();
        this.update_ui(infos);
    }

    /**
     * Build DOM elements.
     */
    init_elements() {
        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/css/behavior.css");
        this.shadowRoot.appendChild(link);

        this.playPauseBtn = this.add_button_to_toolbar("play_arrow");
        this.playPauseBtn.addEventListener("click", async () => {
            const infos = await this.api.toggle_behavior_playback();
            this.update_ui(infos);
        });

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
        span.update = () => {
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

    /**
     * Update attention span elements.
     *
     * @param {Number} duration Attention span time duration in seconds.
     */
    update_attention_span_slider(duration) {
        const value = duration / MAX_ATTENTION_SPAN * N_TICKS;
        this.attentionSpanSlider.value = value;
        this.attentionSpanSpan.update();
    }

    /**
     * Update all UI elements.
     *
     * @param {Object} infos Behavior info object.
     */
    update_ui(infos) {
        this.playPauseBtn.innerHTML = infos.active ? "pause" : "play_arrow";
        this.nowPlayingSpan.innerHTML = infos.lastPlayed;
        this.update_attention_span_slider(infos.params.attentionSpan);
        this.statesDiv.childNodes.forEach(stateDiv => {
            const key = stateDiv.getAttribute("name").toLowerCase() + "Motions";
            const motions = infos.params[key];
            stateDiv.querySelectorAll("input[type='checkbox']").forEach(cb => {
                cb.checked = motions.includes(cb.name);
            });
        });
        this.mark_active_state(infos.active ? infos.state.value : -1);
    }

    /**
     * Emit current behavior params to back end.
     */
    async emit_params() {
        const params = {};
        params.attentionSpan = this.attentionSpanSlider.value / N_TICKS * MAX_ATTENTION_SPAN;
        this.statesDiv.childNodes.forEach(stateDiv => {
            const key = stateDiv.getAttribute("name").toLowerCase() + "Motions";
            params[key] = [];
            stateDiv.querySelectorAll("input[type='checkbox']:checked").forEach(cb => {
                params[key].push(cb.name);
            });
        });
        const infos = await this.api.send_behavior_params(params);
        this.update_ui(infos);
    }

    /**
     * New data message callback for web socket.
     *
     * @param {Object} msg Received message to process.
     */
    async behavior_message(msg) {
        this.update_ui(msg);
    }

    async content_message(msg) {
        const names = Object.keys(msg.splines);
        this.populate_motions(names);
        const infos = await this.api.load_behavior_infos();
        this.update_ui(infos);
    }
}

customElements.define("being-behavior", Behavior);
