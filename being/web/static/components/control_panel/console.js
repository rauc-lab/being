/**
 * Console functionality for control panel.
 */
import {get_color} from "/static/js/color_map.js";


/** Maximum log level. */
const MAX_LOG_LEVEL = 50;


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
export class Console {
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
    new_log_message(record) {
        while (this.list.childNodes.length > this.maxlen) {
            this.remove_oldest_log();
        }

        this.records.push(record);

        const li = document.createElement("li");
        this.list.appendChild(li);
        li.innerHTML = record.name + "<i> " + record.message.replaceAll("\n", "<br>") + "</i>";
        li.style.color = get_color(record.levelno / MAX_LOG_LEVEL);

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
        const text = this.records.map(rec => {
            return rec.levelname + " - " + rec.name + " - " + rec.message;
        }).join("\n");
        const input = document.createElement("textarea");
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
    }
}

