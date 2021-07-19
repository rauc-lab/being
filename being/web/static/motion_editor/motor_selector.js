/**
 * @module motor_selector Component around HTML select to keep track of the
 * currently selected motor (or motion player behind the scenes).
 */
import {remove_all_children, add_option} from "/static/js/utils.js";
import {arange} from "/static/js/array.js";
import {Api} from "/static/js/api.js";


/** @const {number} - Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;


/**
 * Do not show select when there is only 1x option.
 *
 * @param {HTMLElement} select HTML select element.
 */
function dont_display_select_when_no_options(select) {
    select.style.display = select.length < 2 ? "none" : "inline";
}


export class MotorSelector {
    constructor(editor, mpSelect, channelSelect) {
        this.editor = editor;
        this.mpSelect = mpSelect;
        this.channelSelect = channelSelect;
        this.api = new Api();

        this.motionPlayers = [];

        this.mpSelect.addEventListener("change", () => {
            this.update_channel_select();
            this.editor.update_default_bbox();
        });
        this.channelSelect.addEventListener("change", () => {
            this.editor.draw_current_spline();
        });
    }

    /**
     * Disable UI components.
     */
    set disabled(value) {
        this.mpSelect.disabled = value;
        this.channelSelect.disabled = value;
    }

    /**
     * Update UI elements.
     */
    update_channel_select() {
        remove_all_children(this.channelSelect);
        const motionPlayer = this.selected_motion_player();
        arange(motionPlayer.ndim).forEach(dim => {
            add_option(this.channelSelect, "Curve " + (dim + 1));
        });
        dont_display_select_when_no_options(this.channelSelect);
        this.editor.init_plotting_lines(motionPlayer.ndim);
    }

    /**
     * Populate select with the currently available motors.
     * 
     * @param {Array} motors List of motor info objects.
     */
    async populate(motionPlayers) {
        this.motionPlayers = motionPlayers;
        remove_all_children(this.mpSelect);
        this.motionPlayers.forEach(async (mp, nr) => {
            add_option(this.mpSelect, "Motor" + (nr + 1));  // TODO: This is a lie. It's a "Motion Player"

            // TODO: Bit hacky. Find indices of the actual position value
            // outputs of the connected motors.
            mp.actualValueIndices = [];
            mp.motors.forEach(async motor => {
                const outs = await this.api.get_index_of_value_outputs(motor.id);
                outs.forEach(out => {
                    mp.actualValueIndices.push(out);
                });
            });

        });

        dont_display_select_when_no_options(this.mpSelect);
        this.update_channel_select();
    }

    /**
     * Get motor info for currently selected motor.
     *
     * @returns {object} Motor info dictionary.
     */
    selected_motion_player() {
        return this.motionPlayers[this.mpSelect.selectedIndex];
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
