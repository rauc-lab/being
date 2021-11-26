/**
 * @module draggable Manage mouse events for draggable actions.
 */
import { LEFT_MOUSE_BUTTON } from "/static/js/constants.js";


/**
 * Make some draggable by attaching the necessary event listeners.
 * 
 * @param ele HTML element to make draggable.
 * @param start_drag On start drag callback.
 * @param drag On dragging callback.
 * @param end_drag On end drag callback.
 * @param mouseButton On which mouse button to react to. Left mouse button by default.
 */
export function make_draggable(ele, start_drag, drag, end_drag, mouseButton = LEFT_MOUSE_BUTTON, onShift=false) {
    let startPos = null;
    
    function stop_propagation(evt) {
        evt.stopPropagation();
    }

    /**
     * Enable all event listeners for drag action.
     */
    function enable_drag_listeners() {
        addEventListener("mousemove", drag_internal);
        addEventListener("mouseup", end_drag_internal);
        addEventListener("mouseleave", end_drag_internal);
        addEventListener("keyup", escape_drag_internal);
        addEventListener("click", stop_propagation, true);
        addEventListener("dblclick", stop_propagation, true);
    }


    /**
     * Disable all event listerns of drag action.
     */
    function disable_drag_listeners(moved=false) {
        removeEventListener("mousemove", drag_internal);
        removeEventListener("mouseup", end_drag_internal);
        removeEventListener("mouseleave", end_drag_internal);
        removeEventListener("keyup", escape_drag_internal);
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

    /**
     * Start drag movement.
     * @param {MouseEvent} evt Mouse event.
     */
    function start_drag_internal(evt) {
        if (evt.which !== mouseButton) {
            return;
        }

        if (evt.shiftKey !== onShift) {
            return;
        }

        evt.stopPropagation();
        //disable_drag_listeners();  // TODO(atheler): Do we need this?
        startPos = [evt.clientX, evt.clientY];
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
        const endPos = [evt.clientX, evt.clientY];
        const moved = (evt.clientX !== startPos[0] || evt.clientY !== startPos[1]);
        disable_drag_listeners(moved);
        startPos = null;
        end_drag(evt);
    }
}