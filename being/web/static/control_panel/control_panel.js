import { Widget } from "/static/js/widget.js";
import {switch_button_on, switch_button_off, is_checked } from "/static/js/button.js";
import {Api} from "/static/js/api.js";


function get_enum_value_name(obj) {
    return obj.members[obj.value];
}

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
        this.motors = {};

        this.init_html_elements();
    }

    async connectedCallback() {
        const motorInfos = await this.api.get_motor_infos();
        this.new_motor_message(motorInfos)
    }

    init_html_elements() {
        this._append_link("static/control_panel/control_panel.css");
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Turn motors on / off");
        this.homeBtn = this.add_button_to_toolbar("home", "Home motors");

        this.powerBtn.addEventListener("click", async evt => {
            let motorInfos = {};
            if (is_checked(this.powerBtn)) {
                motorInfos = await this.api.disable_motors();
            } else {
                motorInfos = await this.api.enable_motors();
            }
            this.new_motor_message(motorInfos);
        });

        this.homeBtn.addEventListener("click", async evt => {
            await this.api.home_motors();
        });
    }

    update() {
        let enabled = true;
        let homing = 4;
        for (const [motorId, motor] of Object.entries(this.motors)) {
            enabled &= motor.enabled;
            homing = Math.min(homing, motor.homing.value);
        }

        if (enabled) {
            switch_button_on(this.powerBtn);
        } else {
            switch_button_off(this.powerBtn);
        }

        const homingClasses = ["homing-failed", "homing-unhomed", "homing-ongoing", "homing-homed" ];
        this.homeBtn.classList.remove(...homingClasses);
        this.homeBtn.classList.add( homingClasses[homing]);
    }

    new_motor_message(msg) {
        if (msg.type === "motor-update") {
            this.motors[msg.id] = msg;
        } else if (msg.type === "motor-updates") {
            msg.motors.forEach(motor => {
                this.motors[motor.id] = motor;
            });
        } else {
            throw "Unsupported message type: " + msg.type;
        }

        this.update();
    }
}

customElements.define("being-control-panel", ControlPanel);
