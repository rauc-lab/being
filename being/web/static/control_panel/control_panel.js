/**
 * Control panel widget with console.
 */
import {Api} from "/static/js/api.js";
import {Widget} from "/static/js/widget.js";
import {get_color} from "/static/js/color_map.js";
import {switch_button_on, switch_button_off, is_checked} from "/static/js/button.js";


/** Maximum log level. */
const MAX_LOG_LEVEL = 50;


/**
 * Get name of enum value.
 */
function get_enum_value_name(obj) {
    return obj.members[obj.value];
}


/**
 * Get current time in seconds.
 */
function time() {
    return Date.now() / 1000;
}


/**
 * Console logic. Feeds new log messages in an associated ul list element. Has
 * *block auto scrolling* functionality -> Turn off auto scrolling when cursor
 * is over ul list element.
 */
class Console {
    constructor(list, maxlen=50) {
        this.list = list
        this.maxlen = maxlen;
        this.blockedUntil = -Infinity;
        this.list.addEventListener("mouseover", () => {
            this.blockedUntil = Infinity;
        });
        this.list.addEventListener("mouseleave", () => {
            this.blockedUntil = time() + 2;
        });
    }

    /**
     * Check if auto scrolling enabled.
     */
    get auto_scrolling() {
        const now = time();
        return now >= this.blockedUntil;
    }

    /**
     * Remove oldest log entry from list.
     */
    remove_oldest_log() {
        this.list.removeChild(this.list.childNodes[0]);
    }

    /**
     * Scroll to bottom.
     */
    scroll_all_the_way_down() {
        this.list.scrollTop = this.list.scrollHeight;
    }

    /**
     * Process new log record.
     */
    new_log_message(msg) {
        while (this.list.childNodes.length > this.maxlen) {
            this.remove_oldest_log();
        }

        const li = document.createElement("li");
        this.list.appendChild(li);
        li.innerHTML = msg.name + "<i> " + msg.message.replaceAll("\n", "<br>") + "</i>";
        li.style.color = get_color(msg.level / MAX_LOG_LEVEL);
        if (this.auto_scrolling) {
            this.scroll_all_the_way_down();
        }
    }
}


class ControlPanel extends Widget {
    constructor() {
        super();
        this.api = new Api();
        this.motors = {};
        this.console = null;
        this.init_html_elements();
        this.collapse_console();
    }

    init_html_elements() {
        this._append_link("static/control_panel/control_panel.css");

        // Toolbar
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Turn motors on / off");
        this.homeBtn = this.add_button_to_toolbar("home", "Home motors");
        const space = this.add_space_to_toolbar();
        space.style.flexGrow = 1;
        this.consoleBtn = this.add_button_to_toolbar("dehaze");
        this.consoleBtn.style.marginRight = "-2px";
        switch_button_on(this.consoleBtn);

        // Console
        this.consoleList = document.createElement("ul");
        this.consoleList.classList.add("console");
        this.shadowRoot.appendChild(this.consoleList);
        this.console = new Console(this.consoleList);
    }

    /**
     * Collapse console list.
     */
    collapse_console() {
        switch_button_off(this.consoleBtn);
        this.consoleList.style.display = "none";
    }

    /**
     * Expand console list. 
     */
    expand_console() {
        switch_button_on(this.consoleBtn);
        this.consoleList.style.display = "";
    }

    async connectedCallback() {
        const motorInfos = await this.api.get_motor_infos();
        this.new_motor_message(motorInfos)

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

        this.consoleBtn.addEventListener("click", evt => {
            if (is_checked(this.consoleBtn)) {
                this.collapse_console();
            } else {
                this.expand_console();
            }
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

    /**
     * Process new motor update messages. These can be of type "motor-update"
     * or "motor-updates" for batch update of all motors.
     */
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

    /**
     * Process new log message. Relay to console.
     */
    new_log_message(msg) {
        this.console.new_log_message(msg);
    }
}

customElements.define("being-control-panel", ControlPanel);
