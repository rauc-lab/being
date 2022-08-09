/**
 * Control panel widget web component.
 *
 * @module components/control_panel/control_panel
 */
import { draw_block_diagram } from "/static/components/control_panel/block_diagram.js";
import { Console } from "/static/components/control_panel/console.js";
import { Api } from "/static/js/api.js";
import { Widget } from "/static/js/widget.js";
import { switch_button_on, switch_button_off, is_checked, enable_button, disable_button } from "/static/js/button.js";
import { isclose } from "/static/js/math.js";


/** @constant {string} - Control panel widget template. */
const CONTROL_PANEL_TEMPLATE = `
<div class="container" id="control_panel_container">
    <svg id="svg" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
    <ul id="console" class="console"></ul>
</div>
`;


/**
 * Control panel web component widget ``<being-control-panel>``. Holds block
 * network graph and console, animates connection activity.
 */
export class ControlPanel extends Widget {
    constructor() {
        super();
        this.api = new Api();
        this.console = null;
        this.notificationCenter = null;
        this.init_html_elements();
        this.collapse_console();
        this.valueConnections = [];
        this.messageConnections = [];
        this.lastValues = [];
        this.homingState = 4;
        this.motorState = 3;
    }

    /**
     * Associate notification center.
     */
    set_notification_center(notificationCenter) {
        this.notificationCenter = notificationCenter;
    }

    set_visible(visible) {
        if (visible)
            this.container.classList.remove('hide');
        else
            this.container.classList.add('hide');
    }

    /**
     * Initialize HTML elements with shadow dom.
     */
    init_html_elements() {
        this.append_link("static/components/control_panel/control_panel.css");
        this.append_template(CONTROL_PANEL_TEMPLATE);
        this.svg = this.shadowRoot.getElementById("svg");
        this.parametersContainer = this.shadowRoot.getElementById("parameters");
        this.container = this.shadowRoot.getElementById("control_panel_container");

        // Toolbar
        this.powerBtn = this.add_button_to_toolbar("power_settings_new", "Turn motors on / off");
        this.homeBtn = this.add_button_to_toolbar("home", "Home motors");
        const space = this.add_space_to_toolbar();
        space.style.flexGrow = 1;
        this.consoleBtn = this.add_button_to_toolbar("text_snippet", "Toggle console");
        switch_button_on(this.consoleBtn);
        this.copyLogsToClipboardBtn = this.add_button_to_toolbar("content_copy", "Copy console messages to clipboard");
        this.minimizeBtn = this.add_button_to_toolbar("dehaze", "Minimize panel");
        this.minimizeBtn.style.marginRight = "-2px";
        this.minimizeBtn.addEventListener("click", () => {
            let visible = localStorage.getItem('control_panel_visible') === 'true';
            localStorage.setItem('control_panel_visible', (!visible).toString());
            this.set_visible(!visible);
        });
        this.set_visible(localStorage.getItem('control_panel_visible') === 'true');

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
        [this.valueConnections, this.messageConnections] = await draw_block_diagram(this.svg, graph);

        // Connect event listerners
        this.powerBtn.addEventListener("click", async evt => {
            let motors = [];

            switch(this.motorState) {
                case 0:  // Fault
                    motors = await this.api.enable_motors();
                    break;
                case 1:  // Disabled
                    motors = await this.api.enable_motors();
                    break;
                case 2:  // Enabled
                    motors = await this.api.disable_motors();
                    break;
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
     * For new motor info update widget.
     *
     * @param {array} motors - Current motor infos.
     */
    update(motors) {
        this.motorState = 3;  // MotorState.ENABLED + 1...
        this.homingState = 4;  // HomingState.HOMED + 1...
        motors.forEach(motor => {
            this.motorState = Math.min(this.motorState, motor.state.value);
            this.homingState = Math.min(this.homingState, motor.homing.value);
        });

        const hasMotors = motors.length > 0;
        if (hasMotors) {
            enable_button(this.powerBtn);
            const stateClasses = ["state-fault", "state-disabled", "state-enabled"];
            this.powerBtn.classList.remove(...stateClasses);
            this.powerBtn.classList.add(stateClasses[this.motorState]);

            enable_button(this.homeBtn);
            const homingClasses = ["homing-failed", "homing-unhomed", "homing-ongoing", "homing-homed" ];
            this.homeBtn.classList.remove(...homingClasses);
            this.homeBtn.classList.add(homingClasses[this.homingState]);
        } else {
            disable_button(this.powerBtn);
            disable_button(this.homeBtn);
        }
    }

    /**
     * Process new motor update messages. These can be of type "motor-update"
     * or "motor-updates" for batch update of all motors.
     * 
     * @param {Object} msg - Motor update message. Either for a single or
     *     multiple motors.
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
     *
     * @param {Object} msg - Log message.
     */
    new_log_message(msg) {
        this.console.new_log_message(msg);
    }

    /**
     * Process being-state messages. Check for new messages and trigger message
     * connection dot animation.
     *
     * @param {Object} msg - Being state message.
     */
    new_being_state_message(msg) {
        // this.messageConnections.forEach(con => {
        //     const ms = msg.messages[con.index];
        //     if (ms.length) {
        //         con.trigger();
        //     }
        // });
        //
        // if (this.lastValues !== []) {
        //     this.valueConnections.forEach(con => {
        //         if (isclose(msg.values[con.index], this.lastValues[con.index], 1e-3)) {
        //             con.pause();
        //         } else {
        //             con.play();
        //         }
        //     });
        // }
        //
        // this.lastValues = msg.values;
    }

    /**
     * Set flowing state / animation of value connection.
     *
     * @param {boolean} flowing - Flow state true / false
     */
    set_value_connection_flow(flowing) {
        this.valueConnections.forEach(con => {
            if (flowing) {
                con.play();
            } else {
                con.pause();
            }
        });
    }
}

customElements.define("being-control-panel", ControlPanel);
