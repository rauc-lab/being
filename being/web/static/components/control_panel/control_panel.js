/**
 * Control panel widget with console.
 */
import {Api} from "/static/js/api.js";
import {Widget} from "/static/js/widget.js";
import {get_color} from "/static/js/color_map.js";
import {switch_button_on, switch_button_off, is_checked} from "/static/js/button.js";
import {draw_block_diagram} from "/static/components/control_panel/block_diagram.js";


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
        this.records = [];
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
        this.records.shift();
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

        const record = msg.level + " - " + msg.name + " - " + msg.message;
        this.records.push(record);

        if (this.auto_scrolling) {
            this.scroll_all_the_way_down();
        }
    }

    /**
     * Copy current log messages to clipboard.
     */
    copy_log_records_to_clipboard() {
        // Copy record texts to clipboard via dummy input element.
        // Note: document.execCommand instead of the newer clipboard API so
        // that not dependent on a seconds SSL / HTTPS connection.
        const text = this.records.join("\n");
        const input = document.createElement("textarea");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
    }
}


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
    }

    set_notification_center(notificationCenter) {
        this.notificationCenter = notificationCenter;
    }

    init_html_elements() {
        this._append_link("static/components/control_panel/control_panel.css");

        this.add_template(CONTROL_PANEL_TEMPLATE);

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
        draw_block_diagram(this.shadowRoot.getElementById("svg"), graph);

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
}
