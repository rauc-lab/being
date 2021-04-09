/**
 * @module live_plotter Live plotter HTML web component widget.
 */
import { CurverBase } from "/static/js/curver.js";
import { Line } from "/static/js/line.js";


/**
 * Live plotter.
 */
class Plotter extends CurverBase {
    constructor() {
        super();
        this.recBtn = this.add_button("fiber_manual_record", "Record Motor", "btn-rec");
        this.recBtn.addEventListener("click", evt => this.record_signal(evt));
    }

    /**
     * Is currently recording property.
     */
    get recording() {
        // TODO: Good idea to store recording state in buttons checked attribute?
        return this.recBtn.hasAttribute("checked");
    }

    /**
     * Process new data message from backend.
     */
    new_data(msg) {
        while (this.lines.length < msg.values.length) {
            const color = this.colorPicker.next();
            this.lines.push(new Line(this.ctx, color));
        }

        msg.values.forEach((value, nr) => {
            this.lines[nr].append_data([msg.timestamp, value]);
        });
    }

    /**
     * Record selected signal 
     */
    record_signal() {
        this.recBtn.toggleAttribute("checked");
    }
}

customElements.define("being-plotter", Plotter);