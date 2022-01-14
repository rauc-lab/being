/**
 * Curve drawing and editing.
 *
 * @module components/editor/drawer
 */
import { Plotter } from "/static/components/plotter.js";
import { add_arrays, arange, multiply_scalar, subtract_arrays, } from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { make_draggable } from "/static/js/draggable.js";
import { clip } from "/static/js/math.js";
import { Degree, FIRST_CP, KNOT, LEFT, RIGHT, SECOND_CP, } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import {
    arrays_equal, assert, clear_array, emit_custom_event, last_element,
    remove_all_children,
} from "/static/js/utils.js";


/**
 * Nice float formatting with max precision and "0" for small numbers.
 *
 * @param {number} number - Input number.
 * @param {number} [precision=3] - Decimal place.
 * @param {number} [smallest=3] - Absolute lower bound for zero.
 *
 * @returns {string} Formatted number.
 */
function format_number(number, precision = 3, smallest = 1e-10) {
    if (Math.abs(number) < smallest) {
        return "0";
    }

    return number.toPrecision(precision);
}


/**
 * Clip point so that it lies within bounding box.
 *
 * @param {array} pt - 2D point to clip.
 * @param {BBox} bbox - Bounding box to use to restrict the point.
 *
 * @returns {array} Clipped point.
 */
function clip_point(pt, bbox) {
    return [
        clip(pt[0], bbox.ll[0], bbox.ur[0]),
        clip(pt[1], bbox.ll[1], bbox.ur[1]),
    ];
}


/**
 * Find index where to insert value in sorted array. Left sided.
 *
 * @param {array} arr - Sorted array to search.
 * @param {number} value - Search value.
 *
 * @returns {number} Index where to insert value to preserve order.
 */
function searchsorted_left(arr, value) {
    let left = 0;
    let right = arr.length;
    while (left < right) {
        const mid = Math.floor(0.5 * (left + right));
        if (arr[mid] < value) {
            left = mid + 1;
        } else {
            right = mid
        }
    }

    return left;
}


/**
 * Find index where to insert value in sorted array. Right sided.
 *
 * @param {array} arr - Sorted array to search
 * @param {number} value - Search value.
 *
 * @returns {number} Index where to insert value to preserve order.
 */
function searchsorted_right(arr, value) {
    let left = 0;
    let right = arr.length;
    while (left < right) {
        const mid = Math.floor(0.5 * (left + right));
        if (arr[mid] <= value) {
            left = mid + 1;
        } else {
            right = mid;
        }
    }

    return right;
}


/**
 * Sort number array the right way. Will not work for Infinity and Nan values.
 *
 * @param {array} arr - Input array.
 *
 * @returns {array} Sorted copy of array.
 *
 * @example
 * // returns actually [0, 1, 2, 3, 8, 9, 10]
 * sorted_numbers([10, 9, 8, 3, 2, 1, 0])
 */
export function sorted_numbers(arr) {
    const ret = [...arr];
    // Mozilla compare function for sorting number arrays without Infinity or NaN
    // https://developer.mozilla.org/de/docs/Web/JavaScript/Reference/Global_Objects/Array/sort
    ret.sort((a, b) => a - b);
    return ret;
}


/**
 * Data container for snapping positions to horizontal grid (snap to grid
 * feature).
 */
export class Grid {
    /**
     * @param {number} [abs_tol=0.001] - Absolute tolerance.
     */
    constructor(abs_tol = 0.001) {
        this.abs_tol = abs_tol;
        this.yValues = [];
    }

    /**
     * Clear grid values.
     */
    clear() {
        clear_array(this.yValues);
    }

    /**
     * Add y value to grid.
     */
    add_y_value(y) {
        const index = searchsorted_left(this.yValues, y);
        this.yValues.splice(index, 0, y);
    }

    /**
     * Remove y value from grid.
     */
    remove_y_value(y) {
        const index = this.yValues.indexOf(y);
        this.yValues.splice(index, 1);
    }

    /**
     * Snap y value to grid.
     *
     * @param {number} y - Horizontal value to snap.
     *
     * @returns {number} Snapped y value.
     */
    _snap_y_value(y) {
        if (this.yValues.length > 0) {
            const idx = searchsorted_left(this.yValues, y);
            if (idx < this.yValues.length) {
                const candidate = this.yValues[idx];
                const dist = Math.abs(candidate - y);
                if (dist < this.abs_tol) {
                    return candidate;
                }
            }
        }

        return y;
    }

    /**
     * Snap point to grid.
     *
     * @param {array} pt - 2D point.
     *
     * @returns {array} Snapped 2D point.
     */
    snap_point(pt) {
        return [pt[0], this._snap_y_value(pt[1])];
    }

    /**
     * Update grid values from spline.
     *
     * @param {BPoly} spline - Input spline.
     */
    update_from_spline(spline) {
        arange(spline.n_segments + 1).forEach(knotNr => {
            const [_, y] = spline.point(knotNr, KNOT);
            this.add_y_value(y);
        })
    }
}


/**
 * Annotation wrapper. Manages single HTML span element for overlaying
 * informations while dragging.
 *
 * .. figure:: ../images/annotation.png
 *    :width: 50%
 *    :alt: Annotation screenshot.
 *
 *    Annotation shows the current time / position value when dragging a knot.
 *    When dragging a control point it will show the derivative at the adjacent
 *    knot instead.
 *
 * @param {Drawer} drawer - Parent drawer instance.
 */
export class Annotation {
    constructor(drawer) {
        this.drawer = drawer;
        this.span = document.createElement("span");
        this.span.classList.add("annotation");
        drawer.shadowRoot.appendChild(this.span);
    }

    /**
     * Move annotate label around.
     *
     * @param {array} pos - Position to move to (data space).
     * @param {number} offset - Offset value.
     */
    move(pos, offset = 10) {
        const [x, y] = this.drawer.transform_point(pos);
        const bbox = this.span.getBoundingClientRect();
        const width = this.drawer.canvas.width;
        const height = this.drawer.canvas.height;
        this.span.style.left = Math.min(x + offset, width - bbox.width) + "px";
        this.span.style.top = Math.max(y - offset - bbox.height, 0) + "px";
    }

    /**
     * Set inner HTML of annotation label.
     *
     * @param {string} text - Annotation text.
     */
    annotate(text) {
        this.span.innerHTML = text;
    }

    /**
     * Show annotation.
     */
    show() {
        this.span.style.visibility = "visible";
    }

    /**
     * Hide annotation.
     */
    hide() {
        this.span.style.visibility = "hidden";
    }
}


/**
 * Data container for selected knot indices.
 *
 * .. figure:: ../images/selection.png
 *    :alt: Selection screenshot.
 *
 *    Knot numbers `1` and `2` are both selected.
 */
export class Selection {
    constructor() {
        this.set = new Set();
    }

    /**
     * Check if number is selected.
     *
     * @param {number} nr - Number to check.
     *
     * @returns {boolean} If number is selected.
     */
    is_selected(nr) {
        return this.set.has(nr);
    }

    /**
     * If nothing is selected.
     *
     * @returns {boolean} If nothing is selected.
     */
    is_empty() {
        return this.set.size === 0
    }

    /**
     * Select new number.
     *
     * @param {number} nr - Number to select.
     *
     * @returns {boolean} If selection has changed.
     */
    select(nr) {
        return this.set.add(nr);
    }

    /**
     * Deselect number.
     *
     * @param {number} nr - Number to deselect.
     *
     * @returns {boolean} If selection has changed.
     */
    deselect(nr) {
        return this.set.delete(nr);
    }

    /**
     * Clear selection.
     *
     * @returns {boolean} If selection has changed.
     */
    deselect_all() {
        if (this.is_empty()) {
            return false;
        }

        this.set.clear();
        return true;
    }

    /**
     * Get frozen sorted selection.
     *
     * @returns {array} Sorted array copy of selection.
     */
    sorted() {
        return sorted_numbers(this.set);
    }
}


/**
 * Selection rectangle wrapper. Manages the blue shimmering selection box which
 * can be drawn with the mouse.  
 *
 * .. figure:: ../images/selection\ rectangle.png
 *    :alt: Drawer screenshot.
 *
 *    Active selection rectangle.
 *
 * @param {Drawer} drawer - Parent drawer instance.
 */
export class SelectionRectangle {
    constructor(drawer) {
        this.drawer = drawer;
        this.rect = create_element("rect");
        this.rect.classList.add("selection-rectangle");
        this.drawer.svg.appendChild(this.rect);
        this.hide();
    }

    /**
     * Move selection box.
     *
     * @param {number} left - Left side of selection box in data space
     *     coordinates.
     * @param {number} right - Right side of selection box in data space
     *     coordinates.
     */
    move(left, right) {
        const [a, _] = this.drawer.transform_point([left, 0]);
        const [b, __] = this.drawer.transform_point([right, 0]);
        setattr(this.rect, "x", a);
        setattr(this.rect, "y", 0);
        setattr(this.rect, "width", b - a);
        setattr(this.rect, "height", this.drawer.clientHeight);
    }

    /**
     * Show selection box rectangle.
     */
    show() {
        this.rect.style.display = "";
    }

    /**
     * Hide selection box rectangle.
     */
    hide() {
        this.rect.style.display = "none";
    }
}


/** @constant {string} - Drawer template. */
const DRAWER_STYLE = `
<style>
:host {
    user-select: none; /* standard syntax */
    -webkit-user-select: none; /* webkit (safari, chrome) browsers */
    -moz-user-select: none; /* mozilla browsers */
    -khtml-user-select: none; /* webkit (konqueror) browsers */
    -ms-user-select: none; /* IE10+ */
}

.annotation {
    position: absolute;
    visibility: hidden;
    box-shadow: 0 0 10px 10px rgba(255, 255, 255, .666);
    background-color: rgba(255, 255, 255, .666);
}

svg {
    cursor: crosshair;
}

path {
    fill: transparent;
}

path.background {
    stroke: Silver;
    stroke-width: 1;
}

path.middleground {
    stroke: DarkGray;
    stroke-width: 2;
    cursor: pointer;
}

path.foreground {
    stroke: black;
    stroke-width: 2;
    cursor: pointer;
}

.knot {
    fill: black;
    cursor: pointer;
}

.control-point line {
    stroke: black;
}

.control-point circle {
    fill: red;
    cursor: ns-resize;
}

.control-point {
    opacity: 0.1;
    transition: opacity 1.0s ease-out 0.5s;
}

.control-point:hover {
    opacity: 1.0;
    transition: none;
}

.fade-in {
    opacity: 1.0 !important;
    transition: none !important;
}

.selection-rectangle {
    fill: rgba(0, 0, 255, 0.1);
}

.selected {
    filter: drop-shadow(0 0 4px blue);
    cursor: move !important;
}

circle.selected {
    fill: blue;
}

path.selected {
    stroke: blue;
}
</style>
`


/**
 * Curve drawer widget web component. Based on simple value plotter adds curve
 * drawing and editing functionalities.
 *
 * .. figure:: ../images/drawer.png
 *    :alt: Drawer screenshot.
 *
 *    Two splines are plotted. For the foreground spline the black circles are
 *    the knots and the red ones the control points. The thin helper lines
 *    indicate the slope. Knots and control points can be dragged around.
 *
 * Key features:
 *
 * - Foreground / background curves.
 * - Drag mouse motions
 * - Snapping to grid.
 * - Multiple knot selection.
 * - Drag navigation.
 *
 * The plotter base class is used to plot the `actual values` of the motors
 * behind the curves.
 *
 * Emits the following custom events:
 *
 * - ``curvechanging`` when the foreground curve starts to change because of user input.
 * - ``curvechanged`` when the user is done with editing the curve.
 * - ``channelchanged`` when the user clicked on a background curve spline.
 *
 */
export class Drawer extends Plotter {
    constructor() {
        super();
        this.append_template(DRAWER_STYLE);
        this.autoscaling = false;
        this.foregroundCurve = null;
        this.foregroundChannel = null;

        // Attributes which will be overwritten by editor
        this.c1 = true;
        this.snapping_to_grid = true;
        this.limits = new BBox([0, -Infinity], [Infinity, Infinity]);

        // SVG drawing elements
        this.elementGroup = this.svg.appendChild(create_element("g"));
        this.foregroundKnotElements = [];
        this.foregroundPathElements = [];
        this.otherElements = [];

        // Grid
        this.grid = new Grid();

        // Annotation
        this.annotation = new Annotation(this);

        // Knot selection
        this.selection = new Selection();
        this.selectionRect = new SelectionRectangle(this);

        this.setup_global_svg_drag_listeners();
        this.setup_keyboard_shortcuts();
        this.svg.addEventListener("click", evt => {
            this.selection.deselect_all();
            this.update_selected_elements();
        });
        this.svg.addEventListener("dblclick", evt => {
            //evt.stopPropagation();
            if (!this.foregroundCurve) {
                return;
            }

            const wc = this.foregroundCurve.copy();
            const spline = wc.splines[this.foregroundChannel];
            this.emit_curve_changing();
            const pos = this.mouse_coordinates(evt);
            spline.insert_knot(pos);
            this.emit_curve_changed(wc);
        });
    }

    /**
     * Clear foreground curve and SVG elements but remember selection.
     */
    clear() {
        this.foregroundCurve = null;
        this.foregroundChannel = null;
        clear_array(this.foregroundKnotElements);
        clear_array(this.foregroundPathElements);
        clear_array(this.otherElements);
        remove_all_children(this.elementGroup);
    }

    /**
     * Forget everything selected.
     */
    forget_selection() {
        this.selection.deselect_all();
        this.update_selected_elements();
    }

    /**
     * Same as clear() but also forget selection.
     */
    clear_and_forget() {
        this.clear();
        this.forget_selection();
    }

    /**
     * Setup drag handlers for SVG. Either:
     * 
     * a) Draw selection rectangle box
     * b) Navigate viewport. Horizontal shifts / vertical zooms around middle focal point.
     */
    setup_global_svg_drag_listeners() {
        let shiftPressed = false; // Remember on mouse down if shift key was pressed

        // Drag navigation
        let clientStartPos = null; // Initial start position in client space coordinates
        let original = null; // Original viewport copy
        let focal = 0; // Horizontal x coordinate of "focal point"

        // Selection rectangle
        let startPos = null; // Initial start position in data space coordinates
        let xs = []; // Knot values

        const callbacks = {
            "start_drag": evt => {
                if (evt.shiftKey) {
                    shiftPressed = true;

                    this.autoscaling = false;
                    clientStartPos = [evt.clientX, evt.clientY];
                    original = this.viewport.copy();
                    const pt = this.mouse_coordinates(evt);
                    const alpha = clip((pt[0] - original.left) / original.width, 0, 1);
                    focal = original.left + alpha * original.width;
                } else {
                    shiftPressed = false;

                    startPos = this.mouse_coordinates(evt);
                    xs = this.foregroundCurve.splines[this.foregroundChannel].x;
                }
            },
            "drag": evt => {
                if (shiftPressed) {
                    // Affine transform viewport around focal point
                    const clientPos = [evt.clientX, evt.clientY];
                    const delta = subtract_arrays(clientPos, clientStartPos);
                    const shift = -delta[0] / this.canvas.width * original.width;
                    const factor = Math.exp(-0.01 * delta[1]);
                    this.viewport.left = factor * (original.left - focal + shift) + focal;
                    this.viewport.right = factor * (original.right - focal + shift) + focal;
                    this.update_transformation_matrices();
                    this.draw();
                } else {
                    // Selection rectangle box region
                    const pos = this.mouse_coordinates(evt);
                    const left = Math.min(startPos[0], pos[0]);
                    const right = Math.max(startPos[0], pos[0]);
                    this.selectionRect.move(left, right);
                    this.selectionRect.show();

                    // Selected knots inside selection rectangle box
                    const lo = searchsorted_left(xs, left);
                    const hi = searchsorted_right(xs, right);
                    xs.forEach((_, i) => {
                        if (lo <= i && i < hi) {
                            this.selection.select(i);
                        } else {
                            this.selection.deselect(i);
                        }
                    });
                    this.update_selected_elements();
                }
            },
            "end_drag": evt => {
                clientStartPos = null;
                original = null;
                focal = 0;
                startPos = null;
                xs = [];
                shiftPressed = false;
                this.selectionRect.hide();
            },
        };
        make_draggable(this.svg, callbacks);
    }

    /**
     * Setup global key event listeners.
     */
    setup_keyboard_shortcuts() {
        const moveDirections = {
            "ArrowLeft": [-0.5, 0],
            "ArrowRight": [0.5, 0],
            "ArrowUp": [0, 0.01],
            "ArrowDown": [0, -0.01],
        };
        addEventListener("keydown", evt => {
            switch (evt.key) {
                case "Backspace":
                    if (!this.selection.is_empty()) {
                        const knotNumbers = this.selection.sorted();
                        this.selection.deselect_all();
                        this.remove_knots(this.foregroundCurve, this.foregroundChannel, knotNumbers);
                    }
                    break;
                case "Shift":
                    this.svg.style.cursor = "move";
                    break;
                case "ArrowLeft":
                case "ArrowRight":
                case "ArrowUp":
                case "ArrowDown":
                    evt.preventDefault();
                    let offset = moveDirections[evt.key];
                    if (evt.shiftKey) {
                        offset = multiply_scalar(.1, offset);
                    }
                    this.remember_selected_knot_positions();
                    this.emit_curve_changing();
                    this.move_selected_knots(offset);
                    this.emit_curve_changed(this.foregroundCurve);
                    break;
            }
        });

        addEventListener("keyup", evt => {
            if (evt.key === "Shift") {
                this.svg.style.cursor = "";
            }
        });
    }

    /**
     * Update selection styling for foreground elements.
     */
    update_selected_elements() {
        this.foregroundKnotElements.forEach((circle, nr) => {
            if (this.selection.is_selected(nr)) {
                circle.classList.add("selected");
            } else {
                circle.classList.remove("selected");
            }
        });
        this.foregroundPathElements.forEach((path, nr) => {
            const left = this.selection.is_selected(nr);
            const right = this.selection.is_selected(nr + 1);
            if (left || right) {
                path.classList.add("selected");
            } else {
                path.classList.remove("selected");
            }
        });
    }

    /**
     * Remove knots from curve channel spline.
     *
     * @param {Curve} curve - Curve in question.
     * @param {number} channel - Spline number.
     * @param {array} knotNumbers - Knot indices to remove.
     */
    remove_knots(curve, channel, knotNumbers) {
        const wc = curve.copy()
        const spline = wc.splines[channel];
        if (spline.n_segments <= 1) {
            return;
        }

        this.emit_curve_changing();
        sorted_numbers(knotNumbers).forEach((nr, i) => {
            if (spline.n_segments > 1) {
                spline.remove_knot(nr - i);
            }
        });
        this.emit_curve_changed(wc);
    }

    /**
     * Remember current knot positions of working copy. Necessary to then move
     * the knots around.
     */
    remember_selected_knot_positions() {
        const spline = this.foregroundCurve.splines[this.foregroundChannel];
        const numbers = this.selection.sorted();
        this.initialPositions = numbers.map(knotNr => {
            return Array.from(spline.point(knotNr, KNOT)) // Note: Flat array copy!
        });
    }

    /**
     * Move all selected knots by some offset.
     * :func:`Drawer.remember_selected_knot_positions()` has to be called
     * before!
     *
     * @param {number} offset - Horizontal offset.
     * @param {boolean} [snap=false] - Snap to grid.
     */
    move_selected_knots(offset, snap = false) {
        const spline = this.foregroundCurve.splines[this.foregroundChannel];
        const numbers = this.selection.sorted();
        assert(numbers.length === this.initialPositions.length, "Rembered knot positions not up to date!");
        numbers.forEach((knotNr, i) => {
            let target = add_arrays(this.initialPositions[i], offset);
            if (snap) {
                target = this.grid.snap_point(target)
            }

            spline.position_knot(knotNr, target, this.c1);
        });
    }

    /**
     * Process click on selected element:
     * 
     * 1) If already selected continue
     * 2) If not selected:
     * 
     *    a) Without shift key: Overwrite selection
     *    b) With shift key: Add to selection.
     *
     * @param {array} knotNumbers - Knot numbers which got clicked.
     * @param {boolean} shiftKey - If shift key was held.
     */
    click_select_knots(knotNumbers, shiftKey) {
        const somethingSelected = !this.selection.is_empty();
        const adjacent = !knotNumbers.some(nr => this.selection.is_selected(nr));
        if (somethingSelected && adjacent && !shiftKey) {
            this.selection.deselect_all();
        }

        knotNumbers.forEach(nr => this.selection.select(nr));
        this.update_selected_elements();
    }

    /**
     * Initialize an SVG path element and adds it to the SVG parent element.
     * data_source callback needs to deliver the 2-4 Bézier control points.
     *
     * @param {function} data_source - Callable data source returning the
     *     control points.
     *
     * @returns {SVGPathElement} SVG path element.
     */
    create_svg_path(data_source) {
        const path = create_element("path");
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(data_source())));
        };

        return path;
    }

    /**
     * Initialize an SVG circle element and adds it to the SVG parent element.
     * data_source callback needs to deliver the center point of the circle.
     *
     * @param {function} data_source - Callable data source returning the
     *     center point.
     * @param {number} radius - Circle radius.
     *
     * @returns {SVGCircleElement} SVG circle element.
     */
    create_svg_circle(data_source, radius) {
        const circle = create_element("circle");
        setattr(circle, "r", radius);
        circle.draw = () => {
            const center = this.transform_point(data_source());
            setattr(circle, "cx", center[0]);
            setattr(circle, "cy", center[1]);
        };

        return circle;
    }

    /**
     * Initialize an SVG line element and adds it to the SVG parent element.
     * data_source callback needs to deliver the start end and point of the
     * line.
     *
     * @param {function} data_source - Callable data source which spits out the
     *     current start and end point of the line.
     *
     * @returns {SVGLineElement} SVG line instance.
     */
    create_svg_line(data_source) {
        const line = create_element("line");
        line.draw = () => {
            const [start, end] = this.transform_points(data_source());
            setattr(line, "x1", start[0]);
            setattr(line, "y1", start[1]);
            setattr(line, "x2", end[0]);
            setattr(line, "y2", end[1]);
        };

        return line;
    }

    /**
     * Emit custom `curvechanging` event.
     *
     * @param {array} [position=null] - Optional position value to trigger live
     *     preview.
     */
    emit_curve_changing(position = null) {
        emit_custom_event(this, "curvechanging", {
            position: position,
        });
    }

    /**
     * Emit custom `curvechanged` event.
     *
     * @param {Curve} newCurve - New final curve.
     */
    emit_curve_changed(newCurve) {
        emit_custom_event(this, "curvechanged", {
            newCurve: newCurve,
        });
    }

    /**
     * Emit custom `channelchanged` event. When user clicks on another channel
     * of the foreground curve.
     *
     * @param {number} channel - Channel number.
     */
    emit_channel_changed(channel) {
        emit_custom_event(this, "channelchanged", {
            channel: channel,
        });
    }

    /**
     * Make something draggable inside data space. Wraps default make_draggable
     * function. Handles mouse -> image space -> data space transformation,
     * calculates delta offset, triggers redraws. Mostly used to drag SVG
     * elements around.
     *
     * @param {SVGElement} ele - Element to make draggable.
     * @param {Curve} curve - working copy of the curve.
     * @param {number} channel - Active curve channel number.
     * @param {object} callbacks - Drag event callbacks (start_drag, drag, end_drag).
     */
    make_draggable(ele, curve, channel, callbacks = {}) {
        const no_action = (evt, pos) => {};
        callbacks = Object.assign({
            "start_drag": no_action,
            "drag": no_action,
            "end_drag": no_action,
        }, callbacks);

        const spline = curve.splines[channel];
        let startPos = null;

        const outerCallbacks = {
            "start_drag": evt => {
                startPos = this.mouse_coordinates(evt);
                this.grid.update_from_spline(spline);
                this.emit_curve_changing()
                if (ele.parentNode) {
                    ele.parentNode.classList.add("fade-in");
                }

                const snap = this.snapping_to_grid & !evt.shiftKey;
                if (snap) {
                    startPos = this.grid.snap_point(startPos);
                }

                callbacks.start_drag(evt, startPos);

                // Removed selected points from grid
                this.selection.set.forEach(knotNr => {
                    const [_, y] = spline.point(knotNr, KNOT);
                    this.grid.remove_y_value(y);
                });
            },
            "drag": evt => {
                let pos = this.mouse_coordinates(evt);
                pos = clip_point(pos, this.limits);
                const snap = this.snapping_to_grid & !evt.shiftKey;
                if (snap) {
                    pos = this.grid.snap_point(pos);
                }

                callbacks.drag(evt, pos);

                spline.restrict_to_bbox(this.limits);
                this.annotation.move(pos);
                this.annotation.show();
                this.draw_svg();
            },
            "end_drag": evt => {
                let endPos = this.mouse_coordinates(evt);
                const snap = this.snapping_to_grid & !evt.shiftKey;
                if (snap) {
                    endPos = this.grid.snap_point(endPos);
                }

                const somethingChanged = !arrays_equal(startPos, endPos);
                startPos = null;
                this.annotation.hide();
                if (ele.parentNode) {
                    ele.parentNode.classList.remove("fade-in");
                }

                callbacks.end_drag(evt, endPos);

                this.grid.clear();
                if (somethingChanged) {
                    this.emit_curve_changed(curve)
                }
            },
        };

        ele.addEventListener("click", evt => evt.stopPropagation());
        make_draggable(ele, outerCallbacks);
    }

    /**
     * Plot spline path of curve. This is non-interactive.
     *
     * @param {Curve} curve - Curve to draw path for.
     * @param {number} channel - Active curve channel number.
     * @param {string} className - CSS class name to assigne to path.
     */
    plot_curve_path(curve, channel, className) {
        const spline = curve.splines[channel];
        const segments = arange(spline.n_segments);
        segments.forEach(seg => {
            const path = this.create_svg_path(() => [
                spline.point(seg, 0),
                spline.point(seg, 1),
                spline.point(seg, 2),
                spline.point(seg + 1, 0),
            ]);
            if (className === "foreground") {
                this.foregroundPathElements.push(path);
            } else {
                this.otherElements.push(path);
            }
            this.elementGroup.appendChild(path);
            path.classList.add(className);

            if (className === "middleground") {
                path.addEventListener("click", evt => {
                    evt.stopPropagation(); // Prevents transport cursor to jump
                    this.forget_selection();
                    this.emit_channel_changed(channel);
                });
            } else if (className === "foreground") {
                let startPos = null;
                const callbacks = {
                    "start_drag": (evt, pos) => {
                        startPos = pos;
                        const leftKnot = seg;
                        const rightKnot = seg + 1
                        this.click_select_knots([leftKnot, rightKnot], evt.shiftKey);
                        this.remember_selected_knot_positions();
                    },
                    "drag": (evt, pos) => {
                        const snap = this.snapping_to_grid && !evt.shiftKey;
                        this.emit_curve_changing(pos)
                        const offset = subtract_arrays(pos, startPos);
                        this.move_selected_knots(offset, snap);
                        const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                        this.annotation.annotate(txt);
                    },
                };
                this.make_draggable(path, curve, channel, callbacks);
                path.addEventListener("click", evt => {
                    // Stop bubbling
                    evt.stopPropagation();
                });
            }
        });
    }

    /**
     * Plot interactive control points with helper lines of spline.
     *
     * @param {Curve} curve - Curve to draw control points / helper lines for.
     * @param {number} channel - Active curve channel number.
     *
     * @returns {SVGGroupElement} Group containing all control point elements.
     */
    plot_control_point(curve, channel, knotNr, radius) {
        const spline = curve.splines[channel];
        const cpGroup = create_element("g");
        if (knotNr < spline.n_segments) {
            // Right helper line
            const helperLine = this.create_svg_line(() => [
                spline.point(knotNr, KNOT),
                spline.point(knotNr, FIRST_CP),
            ]);
            this.otherElements.push(helperLine);
            cpGroup.appendChild(helperLine);

            // Right control point
            const controlPoint = this.create_svg_circle(() => spline.point(knotNr, FIRST_CP), radius);
            this.otherElements.push(controlPoint);
            cpGroup.appendChild(controlPoint);

            const callbacks = {
                "drag": (evt, pos) => {
                    spline.position_control_point(knotNr, FIRST_CP, pos[1], this.c1);
                    const slope = spline.get_derivative_at_knot(knotNr, RIGHT);
                    this.annotation.annotate("Slope: " + format_number(slope));
                }
            }

            this.make_draggable(controlPoint, curve, channel, callbacks);
        }

        if (knotNr > 0) {
            // Left helper line
            const helperLine = this.create_svg_line(() => [
                spline.point(knotNr, KNOT),
                spline.point(knotNr - 1, SECOND_CP),
            ]);
            this.otherElements.push(helperLine);
            cpGroup.appendChild(helperLine);

            // Left control point
            const controlPoint = this.create_svg_circle(() => spline.point(knotNr - 1, SECOND_CP), radius);
            this.otherElements.push(controlPoint);
            cpGroup.appendChild(controlPoint);

            const callbacks = {
                "drag": (evt, pos) => {
                    spline.position_control_point(knotNr - 1, SECOND_CP, pos[1], this.c1);
                    const slope = spline.get_derivative_at_knot(knotNr, LEFT);
                    this.annotation.annotate("Slope: " + format_number(slope));
                }
            }

            this.make_draggable(controlPoint, curve, channel, callbacks);
        }

        return cpGroup;
    }

    /**
     * Plot interactive spline knots.
     *
     * @param {Curve} curve - Curve to draw knots from.
     * @param {number} channel - Active curve channel number.
     * @param {number} knotNr - Knot number.
     * @param {number} radius - Radius of knot circle.
     *
     * @returns {SVGCircleElement} Circle knot.
     */
    plot_knot(curve, channel, knotNr, radius) {
        const spline = curve.splines[channel];
        const knotCircle = this.create_svg_circle(() => spline.point(knotNr, KNOT), radius);
        this.foregroundKnotElements.push(knotCircle);
        knotCircle.classList.add("knot");

        let startPos = null;

        const callbacks = {
            "start_drag": (evt, pos) => {
                startPos = pos;
                this.click_select_knots([knotNr], evt.shiftKey);
                this.remember_selected_knot_positions();
            },
            "drag": (evt, pos) => {
                this.emit_curve_changing(pos)
                const offset = subtract_arrays(pos, startPos);
                const snap = this.snapping_to_grid && !evt.shiftKey;
                this.move_selected_knots(offset, snap);
                const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                this.annotation.annotate(txt);
            },
        }

        this.make_draggable(knotCircle, curve, channel, callbacks);
        knotCircle.addEventListener("click", evt => {
            // Stop bubbling
            evt.stopPropagation();
        });
        knotCircle.addEventListener("dblclick", evt => {
            evt.stopPropagation();
            this.selection.deselect_all();
            this.remove_knots(curve, channel, [knotNr]);
        });
        return knotCircle;
    }

    /**
     * Plot single curve channel.
     *
     * @param {Curve} curve - Curve to plot.
     * @param {number} channel - Active curve channel number.
     * @param {string} className - CSS class name to assign to path.
     * @param {number} [radius=6] - Circle radius.
     */
    plot_curve_channel(curve, channel, className, radius = 6) {
        const spline = curve.splines[channel];
        assert(spline.degree <= Degree.CUBIC, `Spline degree ${spline.degree} not supported!`);
        this.plot_curve_path(curve, channel, className);
        if (className === "foreground") {
            const knotCircles = [];
            const knotNumbers = arange(spline.n_segments + 1);
            knotNumbers.forEach(knotNr => {
                // Plot control points and helper lines
                const cpGroup = this.plot_control_point(curve, channel, knotNr, radius)
                cpGroup.classList.add("control-point");
                this.elementGroup.appendChild(cpGroup);

                // Plot knots
                // Note: Knots after control points. SVG order dictates
                // layering. Knots have to stay in front of control points.
                // This is important when knots and control points are
                // collapsing onto each other. Because of this the CSS
                // ".knot:hover + .control-point" selector can not be used.
                // This is why we fallback on the JS + "fade-in" class instead.
                const knotCircle = this.plot_knot(curve, channel, knotNr, radius);
                this.elementGroup.appendChild(knotCircle)
                knotCircle.addEventListener("mouseenter", evt => {
                    cpGroup.classList.add("fade-in");
                });
                knotCircle.addEventListener("mouseleave", evt => {
                    cpGroup.classList.remove("fade-in");
                });
                knotCircles.push(knotCircle)
            });
        }
    }

    /**
     * Draw background curve.
     *
     * @param {Curve} curve - Background curve to draw.
     */
    draw_background_curve(curve) {
        if (curve.n_splines === 0) {
            return;
        }

        curve.splines.forEach((spline, c) => {
            this.plot_curve_channel(curve, c, "background");
        });
        this.draw_svg();
    }

    /**
     * Draw foreground curve. Selected channel will be interactive.
     *
     * @param {Curve} curve - Foreground curve to draw.
     * @param {number} [channel=-1] - Foreground curve to draw. None by
     *     default.
     */
    draw_foreground_curve(curve, channel = -1) {
        if (curve.n_splines === 0) {
            this.selector.clear();
            return;
        }

        const wc = curve.copy();
        wc.splines.forEach((spline, c) => {
            if (c !== channel) {
                this.plot_curve_channel(wc, c, "middleground");
            }
        });

        if (0 <= channel && channel < curve.n_splines) {
            this.plot_curve_channel(wc, channel, "foreground");
            this.foregroundCurve = wc;
            this.foregroundChannel = channel;
            this.update_selected_elements();
        }

        this.draw_svg();
    }

    /**
     * Draw / update all SVG elements.
     */
    draw_svg() {
        this.otherElements.forEach(ele => ele.draw());
        this.foregroundPathElements.forEach(ele => ele.draw());
        this.foregroundKnotElements.forEach(ele => ele.draw());
    }

    /**
     * Draw everything.
     */
    draw() {
        this.draw_canvas();
        this.draw_svg();
    }
}

customElements.define("being-drawer", Drawer);
