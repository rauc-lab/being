/**
 * Button helpers. Wrappers around material icons. Button icon can be specified
 * with the `iconName` string (see `Google Material Design Icon Gallery <https://fonts.google.com/icons>`_
 * for available icons).
 *
 * Toggle buttons are normal buttons with the checked attribute set.
 *
 * @module js/button
 */


/** @const {string} - Checked string literal */
const CHECKED = "checked";


/**
 * Create new material HTML button.
 * @param {string} iconName - Icon name string identifier.
 * @param {string} title - Tooltip for button
 * @returns {HTMLButtonElement} New HTML button.
 */
export function create_button(iconName, title="") {
    const btn = document.createElement("button");
    btn.classList.add("mdc-icon-button");

    const div = document.createElement("div");
    div.classList.add("mdc-icon-button__ripple")
    btn.div = div;
    btn.appendChild(div);

    const i = document.createElement("i");
    i.classList.add("material-icons");
    i.classList.add("mdc-icon-button__icon");
    i.innerHTML = iconName;
    btn.i = i;
    btn.appendChild(i);

    if (title) {
        btn.setAttribute("title", title);
    }

    btn.change_icon = newIconName => i.innerHTML = newIconName;
    return btn;
}


/**
 * Toggle button (toggle checked attribute of HTML button).
 * @param {HTMLButtonElement} btn - Button to toggle.
 */
export function toggle_button(btn) {
    btn.toggleAttribute(CHECKED);
}


/**
 * Switch off toggle button.
 * @param {HTMLButtonElement} btn - Button to switch off.
 */
export function switch_button_off(btn) {
    btn.removeAttribute(CHECKED);
}


/**
 * Switch on toggle button.
 * @param {HTMLButtonElement} btn - Button to switch on.
 */
export function switch_button_on(btn) {
    btn.setAttribute(CHECKED, "");
}


/**
 * Switch toggle button to given state.
 * @param {HTMLButtonElement} btn - Button to switch.
 * @param {boolean} state - Target state.
 */
export function switch_button_to(btn, state) {
    if (state) {
        switch_button_on(btn);
    } else {
        switch_button_off(btn);
    }
}


/**
 * Check if button is toggled (if checked attribute is set).
 * @param {HTMLButtonElement} btn - Button to check.
 * @returns {boolean} If button is checked.
 */
export function is_checked(btn) {
    return btn.hasAttribute(CHECKED);
}


/**
 * Enable button.
 * @param {HTMLButtonElement} btn - Button to enable.
 */
export function enable_button(btn) {
    btn.disabled = false;
}


/**
 * Disable button.
 * @param {HTMLButtonElement} btn - Button to disable.
 */
export function disable_button(btn) {
    btn.disabled = true;
}
