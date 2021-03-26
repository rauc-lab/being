"use strict";
import { remove_all_children, add_option } from "/static/js/utils.js";
import { API } from "/static/js/config.js";


/** Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;


export class MotorSelector {
    constructor(select=null) {
        this.select = select;
        this.motorInfos = [];
    }

    get unselected() {
        return this.select.selectedIndex === NOTHING_SELECTED;
    }

    /**
     * Currently selected motor index.
     */
    get selected_index() {
        return this.select.selectedIndex;
    }


    /**
     * Output value index of setpoint value for currently selected motor.
     */
    get setpointValueIndex() {
        return this.motorInfos[this.selected_index].setpointValueIndex;
    }


    /**
     * Output value index of actual value for currently selected motor.
     */
    get actualValueIndex() {
        return this.motorInfos[this.selected_index].actualValueIndex;
    }

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
        motorInfos.forEach(info => {
            add_option(this.select, "Motor " + info.id);
        });
    }
}
