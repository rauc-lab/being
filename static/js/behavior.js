import { Widget } from "/static/js/widget.js";
import { Api } from "/static/js/api.js";
import { remove_all_children } from "/static/js/utils.js";


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
        super();
        this.api = new Api();
        this.statesDiv = null;

        this.api.fetch_behavior_states().then(stateNames => {
            this.populate_states(stateNames);
            this.api.fetch_splines().then(splines => {
                const names = pluck_motion_names(splines);
                this.populate_motions(names);
            });
        });
    }

    connectedCallback() {
        this.add_button_to_toolbar("play_arrow");

        const link = document.createElement("link");
        link.setAttribute("rel", "stylesheet");
        link.setAttribute("href", "static/behavior.css");
        this.shadowRoot.appendChild(link);

        const container = document.createElement("div");
        container.classList.add("container");
        this.shadowRoot.appendChild(container);

        const label = document.createElement("label");
        container.appendChild(label);
        label.innerHTML = "Attention Span";

        const slider = document.createElement("input");
        container.appendChild(slider);
        slider.setAttribute("type", "range");

        container.appendChild(document.createElement("br"));

        const nowPlayingLabel = document.createElement("label");
        container.appendChild(nowPlayingLabel);
        nowPlayingLabel.innerHTML = "Now playing: ";

        const nowPlayingDiv = document.createElement("span");
        container.appendChild(nowPlayingDiv);
        nowPlayingDiv.innerHTML = "Some motion";

        const statesDiv = document.createElement("div");
        container.appendChild(statesDiv);
        statesDiv.classList.add("states");
        this.statesDiv = statesDiv;
    }

    populate_states(stateNames) {
        remove_all_children(this.statesDiv);
        stateNames.forEach(name => {
            const stateDiv = document.createElement("div");
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
        let counter = 0;
        this.statesDiv.querySelectorAll("ul").forEach(ul => {
            remove_all_children(ul);
            motions.forEach(motion => {
                const li = document.createElement("li");
                ul.appendChild(li);
                const cb = document.createElement("input");
                li.appendChild(cb);
                cb.setAttribute("type", "checkbox");
                const id = counter + motion;
                cb.setAttribute("id", id);
                cb.hidden = true;
                const label = document.createElement("label");
                li.appendChild(label);
                label.setAttribute("for", id);
                label.innerHTML = motion;
                counter += 1;
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

    new_data(msg) {
        if (msg.type === "behavior-update") {
            this.mark_active_state(msg.state.value);
        }
    }
}

customElements.define("being-behavior", Behavior);