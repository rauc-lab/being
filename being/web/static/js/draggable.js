/**
 * @module draggable Manage mouse events for draggable actions.
 */
import { LEFT_MOUSE_BUTTON } from "/static/js/constants.js";


/**
 * Make some draggable by attaching the necessary event listeners.
 * @param ele HTML element to make draggable.
 * @param start_drag On start drag callback.
 * @param drag On dragging callback.
 * @param end_drag On end drag callback.
 * @param mouseButton On which mouse button to react to. Left mouse button by default.
 */
export function make_draggable(ele, start_drag, drag, end_drag,
    mouseButton = LEFT_MOUSE_BUTTON) {
    /**
     * Enable all event listeners for drag action.
     */
    function enable_drag_listeners() {
        addEventListener("mousemove", drag_internal);
        addEventListener("mouseup", end_drag_internal);
        addEventListener("mouseleave", end_drag_internal);
        addEventListener("keyup", escape_drag_internal);
    }


    /**
     * Disable all event listerns of drag action.
     */
    function disable_drag_listeners() {
        removeEventListener("mousemove", drag_internal);
        removeEventListener("mouseup", end_drag_internal);
        removeEventListener("mouseleave", end_drag_internal);
        removeEventListener("keyup", escape_drag_internal);
    }


    /**
     * Start drag movement.
     * @param {MouseEvent} evt Mouse event.
     */
    function start_drag_internal(evt) {
        if (evt.which !== mouseButton) {
            return;
        }

        evt.stopPropagation();
        //disable_drag_listeners();  // TODO(atheler): Do we need this?
        enable_drag_listeners();
        start_drag(evt);
    }

    ele.addEventListener("mousedown", start_drag_internal);


    /**
     * Drag element.
     * @param {MouseEvent} evt Mouse event.
     */
    function drag_internal(evt) {
        evt.preventDefault();
        drag(evt);
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


    /**
     * End dragging of element.
     * @param {MouseEvent} evt Mouse event.
     */
    function end_drag_internal(evt) {
        disable_drag_listeners();
        end_drag(evt);
    }
}
