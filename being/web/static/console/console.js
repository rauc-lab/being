/**
 * @module console Console web component widget.
 */
import { Widget } from "/static/js/widget.js";
import { get_color } from "/static/js/color_map.js";

/** Maximum log level. */
const MAX_LOG_LEVEL = 50;


function time() {
    return Date.now() / 1000;
}


class Console extends Widget {
    constructor(maxlen=50) {
        super();
        this.maxlen = maxlen;

        this._append_link("static/console/console.css");
        this.list = document.createElement("ul");
        this.shadowRoot.appendChild(this.list);
        this.blockedUntil = -Infinity;
    }

    connectedCallback() {
        this.addEventListener("mouseover", () => {
            this.blockedUntil = Infinity;
        });
        this.addEventListener("mouseleave", () => {
            this.blockedUntil = time() + 2;
        });
    }

    get auto_scrolling() {
        const now = time();
        return now >= this.blockedUntil;
    }


    /**
     * Remove oldest log entry from list.
     */
    remove_oldest() {
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
    new_log_messages(record) {
        while (this.list.childNodes.length > this.maxlen) {
            this.remove_oldest();
        }

        const li = document.createElement("li");
        this.list.appendChild(li);
        li.innerHTML = record.name + "<i> " + record.message.replaceAll("\n", "<br>") + "</i>";
        li.style.color = get_color(record.level / MAX_LOG_LEVEL);

        if (this.auto_scrolling)
            this.scroll_all_the_way_down();
    }
}

customElements.define("being-console", Console);
