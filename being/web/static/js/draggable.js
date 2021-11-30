/**
 * @module draggable Manage mouse events for draggable actions.
 */
import { LEFT_MOUSE_BUTTON } from "/static/js/constants.js";


/**
 * Dummy event listener.
 */
function NO_ACTION(evt) {}


/**
 * Stop event propagation.
 */
function stop_propagation(evt) {
    evt.stopPropagation();
}


/**
 * 
 * @param {HTMLElement} ele HTML element to make draggable.
 * @param {Object} callbacks Drag event callbacks:
 *     {Function} start_drag
 *     {Function} drag
 *     {Function} end_drag
 * @param {Object} options Drag options:
 *     mouseButton {Number}: Which mouse button to react to (default is left mouse button).
 *     escapable {Boolean}: End drag by pressing ESC key (default is true).
 *     suppressClicks {Boolean}: End drag by pressing ESC key (default is true).
 */
export function make_draggable(ele, callbacks={}, options={}) {
    callbacks = Object.assign({
        "start_drag": NO_ACTION,
        "drag": NO_ACTION,
        "end_drag": NO_ACTION,
    }, callbacks);
    options = Object.assign({
        "mouseButton": LEFT_MOUSE_BUTTON,
        "escapable": true,
        "suppressClicks": true,
    }, options);
    let startPos = null;


    /**
     * Start drag movement.
     * @param {MouseEvent} evt Mouse event.
     */
    function start_drag_internal(evt) {
        if (evt.which !== options.mouseButton) {
            return;
        }

        evt.stopPropagation();
        startPos = [evt.clientX, evt.clientY];
        enable_drag_listeners();
        callbacks.start_drag(evt);
    }


    /**
     * Drag element.
     * @param {MouseEvent} evt Mouse event.
     */
    function drag_internal(evt) {
        evt.preventDefault();
        callbacks.drag(evt);
    }


    /**
     * End dragging of element.
     * @param {MouseEvent} evt Mouse event.
     */
    function end_drag_internal(evt) {
        const moved = (evt.clientX !== startPos[0] || evt.clientY !== startPos[1]);
        disable_drag_listeners(moved);
        startPos = null;
        callbacks.end_drag(evt);
    }


    /**
     * Enable all event listeners for drag action.
     */
    function enable_drag_listeners() {
        addEventListener("mousemove", drag_internal);
        addEventListener("mouseup", end_drag_internal);
        addEventListener("mouseleave", end_drag_internal);
        addEventListener("keyup", escape_drag_internal);
        if (options.suppressClicks) {
            addEventListener("click", stop_propagation, true);
            addEventListener("dblclick", stop_propagation, true);
        }
    }


    /**
     * Disable all event listerns of drag action.
     */
    function disable_drag_listeners(moved=false) {
        removeEventListener("mousemove", drag_internal);
        removeEventListener("mouseup", end_drag_internal);
        removeEventListener("mouseleave", end_drag_internal);
        removeEventListener("keyup", escape_drag_internal);
        if (options.suppressClicks) {
            if (moved) {
                setTimeout(() => {
                    removeEventListener("click", stop_propagation, true);
                    removeEventListener("dblclick", stop_propagation, true);
                }, 50);
            } else {
                removeEventListener("click", stop_propagation, true);
                removeEventListener("dblclick", stop_propagation, true);
            }
        }
    }


    /**
     * Escape drag by hitting escape key.
     * @param {MouseEvent} evt Mouse event.
     */
    function escape_drag_internal(evt) {
        if (evt.key === "Escape") {
            end_drag_internal(evt);
        }
    }

    ele.addEventListener("mousedown", start_drag_internal);
}
