/**
 * @module motor_selector Component around HTML select to keep track of the
 * currently selected motor (or motion player behind the scenes).
 */
import {remove_all_children, add_option} from "/static/js/utils.js";
import {arange} from "/static/js/array.js";


/** @const {number} - Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;

/** @const {object} - Default motor info dictionary if nothing is selected */
export const DEFAULT_MOTOR_INFOS = [
    {
        "id": -2,
        "actualValueIndices": [0],
        "length": [Infinity],
        "ndim": 1,
    },
];


/**
 * Do not show select when there is only 1x option.
 *
 * @param {HTMLElement} select HTML select element.
 */
function dont_display_select_when_no_options(select) {
    select.style.display = select.length < 2 ? "none" : "inline";
}


export class MotorSelector {
    constructor(editor) {
        this.editor = editor;
        this.motorSelect = null;
        this.channelSelect = null;
        this.motorInfos = [];
    }

    /**
     * Disable UI components.
     */
    set disabled(value) {
        this.motorSelect.disabled = value;
        this.channelSelect.disabled = value;
    }

    /**
     * Update UI elements.
     */
    update_channel_select() {
        remove_all_children(this.channelSelect);
        const motor = this.selected_motor_info();
        arange(motor.ndim).forEach(dim => {
            add_option(this.channelSelect, "Motor " + (dim + 1));  // TODO(atheler): Change back to "Curve " after ECAL workshop
        });
        dont_display_select_when_no_options(this.channelSelect);
    }


    /**
     * Set MotorSelectors HTML selelct elements (indirect DI since selects are
     * inside the toolbar).
     *
     * @param {HTMLElement} motorSelect HTML select element for motor selection.
     * @param {HTMLElement} channelSelect HTML select element for motion channel selection.
     */
    attach_selects(motorSelect, channelSelect) {
        this.motorSelect = motorSelect;
        this.channelSelect = channelSelect;
        motorSelect.addEventListener("change", () => {
            this.update_channel_select();
        });
        channelSelect.addEventListener("change", () => {
            this.editor.draw_current_spline();
        });
    }

    /**
     * Populate select with the currently available motors.
     * 
     * @param {Array} motorInfos List of motor info objects.
     */
    populate(motorInfos) {
        this.motorInfos = motorInfos;
        remove_all_children(this.motorSelect);
        motorInfos.forEach(motor => {
            add_option(this.motorSelect, "Motor" + (motor.id + 1));
        });

        dont_display_select_when_no_options(this.motorSelect);
        this.update_channel_select();
    }

    /**
     * Get motor info for currently selected motor.
     *
     * @returns {object} Motor info dictionary.
     */
    selected_motor_info() {
        return this.motorInfos[this.motorSelect.selectedIndex];
    }

    /**
     * Currently selected motor channel / spline dim.
     *
     * @returns {Number} Index of currently selected motion channel.
     */
    selected_channel() {
        return this.channelSelect.selectedIndex;
    }
}
