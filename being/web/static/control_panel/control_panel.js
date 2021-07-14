import { Widget } from "/static/js/widget.js";
import {switch_button_on, switch_button_off, is_checked } from "/static/js/button.js";
import {Api} from "/static/js/api.js";


class ControlPanel extends Widget {
    constructor() {
        super();
        this.api = null;
        this.attentionSpanSlider = null;
        this.attentionSpanSpan = null;
        this.led = null;
        this.nowPlayingSpan = null;
        this.statesDiv = null;
        this.api = new Api();

        this.init_html_elements();
    }

    async connectedCallback() {
        const motors = await this.api.get_motor_infos();
        motors.forEach(motor => this.new_motor_message(motor));
    }

    init_html_elements() {
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Home motors");
        const homeBtn = this.add_button_to_toolbar("home", "Home motors");

        this.powerBtn.addEventListener("click", async evt => {
            if (is_checked(this.powerBtn)) {
                await this.api.disable_motors();
            } else {
                await this.api.enable_motors();
            }
        });
    }

    new_motor_message(motor) {
        if (motor.enabled) {
            switch_button_on(this.powerBtn);
        } else {
            switch_button_off(this.powerBtn);
        }
    }
}

customElements.define("being-control-panel", ControlPanel);