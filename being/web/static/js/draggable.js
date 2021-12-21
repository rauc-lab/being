/**
 * Make something draggable.
 *
 * @module js/draggable
 */
import { LEFT_MOUSE_BUTTON } from "/static/js/constants.js";


/**
 * Dummy event listener.
 *
 * @param {MouseEvent} evt - Some mouse event.
 */
function NO_ACTION(evt) {}


/**
 * Stop event propagation callback. See `explanation <https://www.youtube.com/watch?v=HgzGwKwLmgM>`_.
 *
 * @param {Event} evt - Some event to stop.
 */
function stop_propagation(evt) {
    evt.stopPropagation();
}


/**
 * Make some element react to click and drag movements. User can provide his /
 * her own event listeners for:
 *   - Start of the drag motion (`start_drag`)
 *   - During the drag motion (`drag`)
 *   - End of drag motion  (`end_drag`)
 * 
 * Further options are:
 *   - `mouseButton` {number}: Which mouse button to react to. Default is left
 *     mouse button.
 *   - `escapable` {boolean}: End drag by pressing ESC key. Default is true.
 *   - `suppressClicks` {boolean}: Suppress normal mouse clicks when dragging
 *     (only normal and double clicks). Default is true.
 *
 * @param {HTMLElement} ele - HTML element to make draggable.
 * @param {Object} callbacks - Drag event callbacks (`start_drag`, `drag` and `end_drag`).
 * @param {Object} options - Additional options.
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
     *
     * @param {MouseEvent} evt - Mouse event.
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
     *
     * @param {MouseEvent} evt - Mouse event.
     */
    function drag_internal(evt) {
        evt.preventDefault();
        callbacks.drag(evt);
    }


    /**
     * End dragging of element.
     *
     * @param {MouseEvent} evt - Mouse event.
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
     * Disable all event listeners of drag action.
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
     *
     * @param {MouseEvent} evt - Mouse event.
     */
    function escape_drag_internal(evt) {
        if (evt.key === "Escape") {
            end_drag_internal(evt);
        }
    }

    ele.addEventListener("mousedown", start_drag_internal);
}
