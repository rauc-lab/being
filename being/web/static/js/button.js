/**
 * @module button Button helper stuff. Helper functions for using buttons as
 * toggle buttons.
 */


/** Checked string literal */
const CHECKED = "checked";


/**
 * Create new HTML button (material-icons class).
 *
 * @param {String} iconName Icon name string identifier.
 * @param {String} title Tooltip for button
 * @returns HTMLButton
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
 * Switch button to given state.
 * 
 * @param {HtmlElement} btn Button to switch.
 * @param {Boolean} state Target state.
 */
export function switch_button_to(btn, state) {
    if (state) {
        switch_button_on(btn);
    } else {
        switch_button_off(btn);
    }
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
