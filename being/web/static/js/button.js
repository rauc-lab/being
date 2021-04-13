/**
 * @module button Button helper stuff. Helper functions for using buttons as
 * toggle buttons.
 */


/** Checked string literal */
const CHECKED = "checked";


/**
 * Create new HTML button (material-icons class).
 *
 * @param {string} innerHTML Inner HTML of button.
 * @param {string} title Tooltip for button
 * @returns HTMLButton
 */
export function create_button(innerHTML, title = "") {
    const btn = document.createElement("button");
    btn.classList.add("material-icons");
    btn.innerHTML = innerHTML;
    btn.title = title;
    return btn;
}


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


/**
 * Enable button.
 *
 * @param {object} btn HTML button.
 */
export function enable_button(btn) {
    btn.disabled = false;
}


/**
 * Disable button.
 *
 * @param {object} btn HTML button.
 */
export function disable_button(btn) {
    btn.disabled = true;
}
