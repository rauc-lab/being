import { Widget } from "/static/js/widget.js";


class Behavior extends Widget {
    constructor() {
        super();
        const ul = document.createElement("ul");
        ["Sleeping", "Chilled", "Excited"].forEach(state => {
            const li = document.createElement("li");
            li.innerHTML = state;
            ul.appendChild(li);
        });
        this.shadowRoot.appendChild(ul);
    }

    connectedCallback() {
        console.log('Behavior.connectedCallback()');
    }
}


customElements.define("being-behavior", Behavior);