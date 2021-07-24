/**
 * Control panel widget with console.
 */
import {Api} from "/static/js/api.js";
import {Widget} from "/static/js/widget.js";
import {switch_button_on, switch_button_off, is_checked} from "/static/js/button.js";
import {draw_block_diagram} from "/static/components/control_panel/block_diagram.js";
import {Console} from "/static/components/control_panel/console.js";


const CONTROL_PANEL_TEMPLATE = document.createElement("template");
CONTROL_PANEL_TEMPLATE.innerHTML = `
<div class="container">
    <svg id="svg" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
    <ul id="console" class="console"></ul>
</div>
`;


export class ControlPanel extends Widget {
    constructor() {
        super();
        this.api = new Api();
        this.console = null;
        this.notificationCenter = null;
        this.init_html_elements();
        this.collapse_console();
        this.messageConnections = [];
    }

    set_notification_center(notificationCenter) {
        this.notificationCenter = notificationCenter;
    }

    init_html_elements() {
        this._append_link("static/components/control_panel/control_panel.css");
        this.add_template(CONTROL_PANEL_TEMPLATE);
        this.svg = this.shadowRoot.getElementById("svg");

        // Toolbar
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Turn motors on / off");
        this.homeBtn = this.add_button_to_toolbar("home", "Home motors");
        const space = this.add_space_to_toolbar();
        space.style.flexGrow = 1;
        this.copyLogsToClipboardBtn = this.add_button_to_toolbar("content_copy", "Copy console messages to clipboard");
        this.consoleBtn = this.add_button_to_toolbar("dehaze", "Toggle console");
        this.consoleBtn.style.marginRight = "-2px";
        switch_button_on(this.consoleBtn);

        // Console
        this.consoleList = this.shadowRoot.getElementById("console");
        this.console = new Console(this.consoleList);
    }

    /**
     * Collapse console list.
     */
    collapse_console() {
        switch_button_off(this.consoleBtn);
        this.copyLogsToClipboardBtn.disabled = true;
        this.consoleList.style.display = "none";
    }

    /**
     * Expand console list. 
     */
    expand_console() {
        switch_button_on(this.consoleBtn);
        this.copyLogsToClipboardBtn.disabled = false;
        this.consoleList.style.display = "";
    }

    async connectedCallback() {
        // Initial data
        const motors = await this.api.get_motor_infos();
        this.update(motors);

        const graph = await this.api.get_graph();
        this.messageConnections = await draw_block_diagram(this.svg, graph);

        // Connect event listerners
        this.powerBtn.addEventListener("click", async evt => {
            let motors = [];
            if (is_checked(this.powerBtn)) {
                motors = await this.api.disable_motors();
            } else {
                motors = await this.api.enable_motors();
            }
            this.update(motors);
        });

        this.homeBtn.addEventListener("click", () => {
            this.api.home_motors();
        });

        this.copyLogsToClipboardBtn.addEventListener("click", () => {
            this.console.copy_log_records_to_clipboard();
            if (this.notificationCenter !== null) {
                this.notificationCenter.notify(
                    "Copied console logs to clipboard"
                )
            }
        });

        this.consoleBtn.addEventListener("click", () => {
            if (is_checked(this.consoleBtn)) {
                this.collapse_console();
            } else {
                this.expand_console();
            }
        });
    }

    /**
     * For new motor infos update widget.
     *
     * @param {Array} motors Current motor infos.
     */
    update(motors) {
        let enabled = true;
        let homing = 4;
        motors.forEach(motor => {
            enabled &= motor.enabled;
            homing = Math.min(homing, motor.homing.value);
        });

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
     * 
     * @param {Object} msg Motor update message. Either for a single or multiple motors.
     */
    new_motor_message(msg) {
        if (msg.type === "motor-update") {
            this.update([msg.motor]);
        } else if (msg.type === "motor-updates") {
            this.update(msg.motors);
        } else {
            throw "Unsupported message type: " + msg.type;
        }
    }

    /**
     * Process new log message. Relay to console.
     */
    new_log_message(msg) {
        this.console.new_log_message(msg);
    }

    /**
     * Process new being-state messages. Check for new messages and trigger
     * message connection dot animation.
     */
    new_being_state_message(msg) {
        this.messageConnections.forEach(con => {
            const ms = msg.messages[con.index];
            if (ms.length) {
                con.trigger();
            }
        })
    }

    /**
     * Set flowing state / animation of value connection.
     * @param {Bool} - flowing Flow state true / false
     */
    set_value_connection_flow(flowing) {
        for (let con of this.svg.getElementsByClassName("connection value")) {
            if (flowing) {
                con.classList.add("flowing")
            } else {
                con.classList.remove("flowing")
            }
        }
    }
}
