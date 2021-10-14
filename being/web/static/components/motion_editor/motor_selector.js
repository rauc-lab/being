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
    constructor(editor, motionPlayerSelect, motorSelect) {
        this.editor = editor;
        this.motionPlayerSelect = motionPlayerSelect;
        this.motorSelect = motorSelect;
        this.api = new Api();

        this.blocks = {};
        this.motionPlayers = [];
        this.actualValueIndices = [];

        this.motionPlayerSelect.addEventListener("change", () => {
            this.update_motor_select();
            this.editor.update_default_bbox();
        });
        this.motorSelect.addEventListener("change", () => {
            this.editor.draw_current_spline();
        });
    }

    /**
     * Disable UI components. Analog to buttons.
     */
    set disabled(value) {
        this.motionPlayerSelect.disabled = value;
        this.motorSelect.disabled = value;
    }

    /**
     * Update UI elements.
     */
    update_motor_select() {
        const motionPlayer = this.selected_motion_player();
        remove_all_children(this.motorSelect);
        motionPlayer.outputNeighbors.forEach(id => {
            const motor = this.blocks[id];
            add_option(this.motorSelect, motor.name);
        });

        //dont_display_select_when_no_options(this.motorSelect);
        this.editor.init_plotting_lines(motionPlayer.ndim);
    }

    /**
     * Populate MotorSelector with available motion players / motors. All being
     * blocks provided for motor lookup.
     * 
     * @param {object} All being blocks. id -> block lookup dictionary.
     */
    async populate(blocks) {
        this.blocks = blocks;

        // Filter motion players
        const motionPlayers = [];
        for (const [id, block] of Object.entries(blocks)) {
            if (block.blockType === "MotionPlayer") {
                motionPlayers.push(block);
            }
        }
        this.motionPlayers = motionPlayers;

        // Lookup indices of actual value outputs for each motion player and its motors
        this.actualValueIndices = [];
        this.motionPlayers.forEach(async mp => {
            const idx = [];
            mp.motors.forEach(async motor => {
                const outs = await this.api.get_index_of_value_outputs(motor.id);
                idx.push(...outs);
            });
            this.actualValueIndices.push(idx);
        });

        // Motion player select
        remove_all_children(this.motionPlayerSelect);
        this.motionPlayers.forEach(async mp => {
            add_option(this.motionPlayerSelect, mp.name);
        });

        dont_display_select_when_no_options(this.motionPlayerSelect);

        // Motor select
        this.update_motor_select();

    }

    /**
     * Get motor info for currently selected motor.
     *
     * @returns {object} Motor info dictionary.
     */
    selected_motion_player() {
        return this.motionPlayers[this.motionPlayerSelect.selectedIndex];
    }

    /**
     * Currently selected motor channel / spline dim.
     *
     * @returns {Number} Index of currently selected motion channel.
     */
    selected_motor_channel() {
        return this.motorSelect.selectedIndex;
    }

    /**
     * Get ValueOutput indices for currently selected motion player. Can be
     * used to lookup the actual output values of the currently selected motors
     * inside the being messages.
     *
     * @returns {Array} Indices of actual value outputs of currently selected motors.
     */
    selected_value_output_indices() {
        return this.actualValueIndices[this.motionPlayerSelect.selectedIndex];
    }
}
