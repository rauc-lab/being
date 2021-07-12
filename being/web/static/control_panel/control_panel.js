import { Widget } from "/static/js/widget.js";


class ControlPanel extends Widget {
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

    init_html_elements() {
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Home motors");
        this.homeBtn = this.add_button_to_toolbar("home", "Home motors");
    }
}

customElements.define("being-control-panel", ControlPanel);
