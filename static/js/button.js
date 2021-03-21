"use strict";
/**
 * Button helper stuff. Helper functions for using buttons as toggle buttons.
 */

/** Checked string literal */
const CHECKED = "checked";


/**
 * Toggle checked attribute of HTML button.
 *
 * @param {object} btn Button to toggle.
 */
export function toggle_button(btn) {
    btn.toggleAttribute(CHECKED);
}


/**
 * Switch toggle HTML button off.
 *
 * @param {object} btn Button to switch off.
 */
export function switch_button_off(btn) {
    btn.removeAttribute(CHECKED);
}


/**
 * Switch toggle HTML button on.
 *
 * @param {object} btn Button to switch on.
 */
export function switch_button_on(btn) {
    btn.setAttribute(CHECKED, "");
}


/**
 * Check if button has checked attribute / is turned on.
 *
 * @param {object} btn HTML button.
 */
export function is_checked(btn) {
    return btn.hasAttribute(CHECKED);
}



export function enable_button(btn) {
    btn.disabled = false;
}


export function disable_button(btn) {
    btn.disabled = true;
}