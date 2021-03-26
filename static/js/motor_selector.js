"use strict";
import { remove_all_children, add_option } from "/static/js/utils.js";


/** Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;


/** Default motor info dictionary if nothing is selected */
const DEFAULT_MOTOR_INFO = {
    "id": 0,
    "setpointValueIndex": 0,
    "actualValueIndex": 0,
    "length": Infinity,
}


export class MotorSelector {
    constructor(select=null) {
        this.select = select;
        this.motorInfos = [];
    }


    /**
     * Set select element (DI).
     *
     * @param {HTMLElement} select HTML select element.
     */
     attach_select(select) {
        this.select = select;
    }


    /**
     * Populate select with the currently available motors.
     *
     * @param {Array} motorInfos List of motor info objects.
     */
    populate(motorInfos) {
        this.motorInfos = motorInfos;
        remove_all_children(this.select);
        motorInfos.forEach(motor => {
            add_option(this.select, "Motor " + motor.id);
        });
    }


    /**
     * Get motor info for currently selected motor.
     *
     * @returns {object} Motor info dictionary.
     */
    selected_motor_info() {
        if (this.select.selectedIndex === NOTHING_SELECTED) {
            return DEFAULT_MOTOR_INFO;
        }

        return this.motorInfos[this.select.selectedIndex];
    }
}