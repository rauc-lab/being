/*jslint browser:true */
"use strict";
import { LEFT_MOUSE_BUTTON, ESC_KEY_CODE } from "/static/js/constants.js";


/**
 * Make some draggable by attaching the necessary event listeners.
 *
 * @param ele - HTML element to make draggable.
 * @param start_drag - On start drag callback.
 * @param drag - On dragging callback.
 * @param end_drag - On end drag callback.
 * @param mouseButton - On which mouse button to react to. Left mouse button by
 * default.
 */
export function make_draggable(ele, start_drag, drag, end_drag,
    mouseButton = LEFT_MOUSE_BUTTON) {
    /**
     * Enable all event listeners for drag action.
     */
    function enable_drag_listeners() {
        addEventListener("mousemove", _drag);
        addEventListener("mouseup", _end_drag);
        addEventListener("mouseleave", _end_drag);
        addEventListener("keyup", _escape_drag);
    }


    /**
     * Disable all event listerns of drag action.
     */
    function disable_drag_listeners() {
        removeEventListener("mousemove", _drag);
        removeEventListener("mouseup", _end_drag);
        removeEventListener("mouseleave", _end_drag);
        removeEventListener("keyup", _escape_drag);
    }


    /**
     * Start drag movement.
     *
     * @param evt - Mouse event.
     */
    function _start_drag(evt) {
        if (evt.which !== mouseButton) {
            return;
        }

        //disable_drag_listeners();  // TODO: Do we need this?
        enable_drag_listeners();
        start_drag(evt);
    }

    ele.addEventListener("mousedown", _start_drag);


    /**
     * Drag element.
     *
     * @param evt - Mouse event.
     */
    function _drag(evt) {
        evt.preventDefault();
        drag(evt);
    }


    /**
     * Escape drag by hitting escape key.
     *
     * @param evt - Mouse event.
     */
    function _escape_drag(evt) {
        if (evt.keyCode === ESC_KEY_CODE) {
            _end_drag(evt);
        }
    }


    /**
     * End dragging of element.
     *
     * @param evt - Mouse event.
     */
    function _end_drag(evt) {
        disable_drag_listeners();
        end_drag(evt);
    }
}
