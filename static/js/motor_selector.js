"use strict";
import { remove_all_children, add_option } from "/static/js/utils.js";
import { HTTP_HOST } from "/static/js/constants.js";


/** Nothing selected in HTML select yet */
export const NOTHING_SELECTED = -1;

export class MotorSelector {
    constructor(select) {
        this.select = select;
        this.motorInfos = [];
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

    motor_url(id) {
        return HTTP_HOST + "/api/motors/" + id;
    }

    /**
     * Motor API url for currently selected motor.
     */
    selected_motor_url() {
        if (this.selected_index === NOTHING_SELECTED) {
            throw "No motor selected yet!";
        }

        return this.motor_url(this.selected_index);
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
