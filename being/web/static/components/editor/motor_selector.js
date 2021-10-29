/**
 * @module motor_selector Component around HTML select to keep track of the
 * currently selected motor (or motion player behind the scenes).
 */
import {remove_all_children, add_option } from "/static/js/utils.js";
import {arange} from "/static/js/array.js";
import {Api} from "/static/js/api.js";
import {defaultdict} from "/static/js/utils.js";
import {clip} from "/static/js/math.js";


/** @const {number} - Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;


/**
 * Do not show select when there is only 1x option.
 *
 * @param {HTMLElement} select HTML select element.
 */
export function dont_display_select_when_no_options(select) {
    select.style.display = select.length < 2 ? "none" : "inline";
}


/**
 * Manages selected motion players / motors.
 */
export class MotorSelector {
    /**
     * @param motionPlayerSelect - HTML select element for motion player selection.
     * @param motorSelect - HTML select element for motor channel select.
     */
    constructor(motionPlayerSelect, motorSelect) {
        this.motionPlayerSelect = motionPlayerSelect;
        this.motorSelect = motorSelect;
        this.motionPlayers = [];
        this.actualValueIndices = [];
        this.listeners = defaultdict(Array);

        this.motionPlayerSelect.addEventListener("change", () => {
            this.update_motor_select();
            this.emit_change();
        });
        this.motorSelect.addEventListener("change", () => {
            this.emit_change();
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
     * Continue with initialization (async part).
     */
    async init() {
        const api = new Api();
        this.motionPlayers = await api.get_motion_player_infos();
        remove_all_children(this.motionPlayerSelect);
        this.actualValueIndices = [];
        this.motionPlayers.forEach(async mp => {
            add_option(this.motionPlayerSelect, mp.name);

            // Lookup indices of actual value outputs for each motion player
            // and its motors
            const idx = [];
            mp.motors.forEach(async motor => {
                const outs = await api.get_index_of_value_outputs(motor.id);
                idx.push(...outs);
            });
            this.actualValueIndices.push(idx);
        });
        dont_display_select_when_no_options(this.motionPlayerSelect);
        this.update_motor_select();
    }

    select_motion_player(motionPlayer) {
        console.log("select_motion_player()", motionPlayer);
        const idx = this.motionPlayers.findIndex(mp => mp.id === motionPlayer.id);
        if (idx === NOTHING_SELECTED) {
            console.log("Did not find motionPlayer with id", motionPlayer.id);
        } else {
            this.motionPlayerSelect.selectedIndex = idx;
            this.update_motor_select();
        }
    }

    select_channel(channel) {
        console.log("select_channel()", motionPlayer);
        if (this.is_motion_player_selected()) {
            const mp = this.selected_motion_player();
            channel = clip(channel, 0, mp.ndim - 1);
            this.motorSelect.selectedIndex = channel;
        }
    }


    /**
     * Is any motion player selected? Do we get valid data from
     * selected_motion_player()?
     */
    is_motion_player_selected() {
        return this.motionPlayerSelect.selectedIndex > NOTHING_SELECTED;
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

    emit_change() {
        this.listeners["change"].forEach(callback => {
            callback("change", this.selected_motion_player(), this.selected_motor_channel());
        })
    }

    addEventListener(type, callback) {
        this.listeners[type].push(callback)
    }

    /**
     * Update motor select UI element.
     */
    update_motor_select() {
        const selectedIndex = this.motorSelect.selectedIndex || 0;
        const mp = this.selected_motion_player();
        remove_all_children(this.motorSelect);
        mp.motors.forEach(motor => {
            add_option(this.motorSelect, motor.name);
        });
        this.motorSelect.selectedIndex = clip(selectedIndex, 0, mp.ndim - 1);
        dont_display_select_when_no_options(this.motorSelect);
    }
}
