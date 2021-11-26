/**
 * @module splien_drawer Component for drawing the actual splines inside the spline editor.
 */
import { arange, subtract_arrays, add_arrays } from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { LEFT_MOUSE_BUTTON } from "/static/js/constants.js";
import { make_draggable } from "/static/js/draggable.js";
import { clip } from "/static/js/math.js";
import { Plotter } from "/static/components/plotter.js";
import { COEFFICIENTS_DEPTH, KNOT, FIRST_CP, SECOND_CP, Degree, LEFT, RIGHT } from "/static/js/spline.js";
import { create_element, path_d, setattr, getattr } from "/static/js/svg.js";
import {
    assert, arrays_equal, clear_array, remove_all_children, emit_custom_event,
} from "/static/js/utils.js";


/**
 * Try to snap value to array of grid values. Return value as if not close
 * enough to grid. Exclude value itself as grid line candidate.
 *
 * @param {Number} value Value to snap to grid.
 * @param {Array} grid Grid values.
 * @param {Number} threshold Distance attraction threshold.
 * @returns Snapped value.
 */
function snap_to_value(value, grid, threshold=.001) {
    let ret = value;
    let dist = Infinity;
    grid.forEach(g => {
        if (value !== g) {
            const d = Math.abs(value - g);
            if (d < threshold && d < dist) {
                dist = d;
                ret = g;
            }
        }
    });

    return ret;
}


/**
 * Nice float formatting with max precision and "0" for small numbers.
 */
function format_number(number, precision=3, smallest=1e-10) {
    if (Math.abs(number) < smallest) {
        return "0";
    }

    return number.toPrecision(precision);
}


/**
 * Clip point so that it lies within bounding box.
 *
 * @param {Array} pt 2D point to clip.
 * @param {BBox} bbox Bounding box to use to restrict the point.
 * @returns Clipped point.
 */
function clip_point(pt, bbox) {
    return [
        clip(pt[0], bbox.ll[0], bbox.ur[0]),
        clip(pt[1], bbox.ll[1], bbox.ur[1]),
    ];
}


const EXTRA_STYLE = `
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
}

path.foreground {
    stroke: black;
    stroke-width: 2;
}

.knot {
    fill: black;
    cursor: move;
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

.selection-rectangle {
    fill: rgba(0, 0, 255, 0.1);
}

.pointed {
    cursor: pointer;
}

.fade-in {
    opacity: 1.0 !important;
    transition: none !important;
}

circle.selected {
    fill: blue;
    filter: drop-shadow(0 0 4px blue);
}

path.selected {
    stroke: blue;
    filter: drop-shadow(0 0 4px blue);
}

.no-pointer-events {
    /*pointer-events: none;*/
}

</style>
`


function binary_search(arr, value) {
    if (arr.length === 0) {
        return -1;
    }

    let left = 0;
    let right = arr.length - 1;

    while (left <= right) {
        const mid = Math.floor(0.5 * (left + right));
        if (arr[mid] < value) {
            left = mid + 1;
        } else if (arr[mid] > value) {
            right = mid - 1;
        } else {
            return mid;
        }
    }

    return -1
}


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
 * Drag selection.
 */
class Selector {
    constructor(drawer) {
        this.drawer = drawer;
        this.svg = drawer.svg;
        this.selection = new Set();
        this.spline = null
        this.knotCircles = [];
        this.rect = create_element("rect");
        this.rect.classList.add("selection-rectangle");
        this.rect.style.display = "none";
        this.svg.appendChild(this.rect);
        this.pt = this.svg.createSVGPoint();

        this.setup_drag_selection();
    }

    clear() {
        this.selection.clear();
        this.spline = null;
        clear_array(this.knotCircles);
        this.hide();
    }

    show() {
        this.rect.style.display = "";
    }

    hide() {
        this.rect.style.display = "none";
    }

    mouse_event_position_inside_svg(evt) {
        this.pt.x = evt.clientX;
        this.pt.y = evt.clientY;
        return this.pt.matrixTransform(this.svg.getScreenCTM().inverse());
    }

    move_selection_rect(left, right) {
        setattr(this.rect, "x", left);
        setattr(this.rect, "y", 0);
        setattr(this.rect, "width", right - left);
        setattr(this.rect, "height", this.drawer.clientHeight);
    }

    setup_drag_selection() {
        let start = null;
        let xs = [];
        make_draggable(
            this.svg,
            evt => {
                start = this.mouse_event_position_inside_svg(evt);
                this.knotCircles.forEach(kc => {
                    xs.push(parseInt(getattr(kc, "cx")))
                });
            },
            evt => {
                // Selected region
                const end = this.mouse_event_position_inside_svg(evt);
                const left = Math.min(start.x, end.x);
                const right = Math.max(start.x, end.x);

                this.move_selection_rect(left, right);
                this.show();

                // Find selected knots
                const lo = searchsorted_left(xs, left);
                const hi = searchsorted_right(xs, right);
                this.knotCircles.forEach((kc, i) => {
                    if (lo <= i && i < hi) {
                        kc.classList.add("selected");
                        this.selection.add(i)
                    } else {
                        kc.classList.remove("selected");
                        this.selection.delete(i);
                    }
                });
            },
            evt => {
                start = null;
                xs = [];
                this.hide();
            },
        );
    }

    set_spline(spline) {
        this.spline = spline;
    }

    set_knot_circles(knotCircles) {
        this.knotCircles = knotCircles;
        this.knotCircles.forEach((circle, nr) => {
            if (this.is_selected(nr)) {
                circle.classList.add("selected");
            } else {
                circle.classList.remove("selected");
            }
        });
    }

    is_selected(knotNr) {
        return this.selection.has(knotNr);
    }

    something_is_selected() {
        return this.selection.size > 0;
    }

    select(knotNr) {
        this.selection.add(knotNr);
        this.knotCircles[knotNr].classList.add("selected");
    }

    deselect(knotNr) {
        this.selection.delete(knotNr);
        this.knotCircles[knotNr].classList.remove("selected");
    }

    deselect_all() {
        this.selection.forEach(nr => this.deselect(nr));
    }

    selected_knot_array() {
        const knotNumbers = Array.from(this.selector.selection);
        return knotNumbers.sort();
    }
}



class Selection {
    constructor() {
        this.set = new Set();
    }

    select(nr) {
        return this.set.add(nr);
    }

    deselect(nr) {
        return this.set.delete(nr);
    }

    is_selected(nr) {
        return this.set.has(nr);
    }

    is_empty() {
        return this.set.size === 0
    }

    deselect_all() {
        if (this.is_empty()) {
            return false;
        }

        this.set.clear();
        return true;
    }

    sort() {
        return Array.from(this.set).sort()
    }
}


export class Drawer extends Plotter {
    constructor() {
        super();
        this.append_template(EXTRA_STYLE);
        this.annotation = document.createElement("span");
        this.annotation.classList.add("annotation");
        this.shadowRoot.appendChild(this.annotation);
        this.autoscaling = false;

        this.elementGroup = this.svg.appendChild(create_element("g"));

        this.foregroundKnotElements = [];
        this.foregroundPathElements = [];
        this.otherElements = [];

        this.c1 = true;
        this.snapping_to_grid = true;
        this.limits = new BBox([0, -Infinity], [Infinity, Infinity]);

        //this.setup_svg_drag_navigation();
        this.setup_keyboard_shortcuts();

        this.foregroundCurve = null;
        this.foregroundChannel = null;

        this.selection = new Selection();

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
     * Clear everything.
     */
    clear() {
        clear_array(this.foregroundKnotElements);
        clear_array(this.foregroundPathElements);
        clear_array(this.otherElements);
        remove_all_children(this.elementGroup);
    }

    /**
     * Setup drag event handlers for moving horizontally and zooming
     * vertically.
     */
    setup_svg_drag_navigation() {
        let start = null;
        let orig = null;
        let mid = 0;

        const mouseButton = LEFT_MOUSE_BUTTON;
        const onShift = true;  // Only react when shift key is pressed
        make_draggable(
            this.svg,
            evt => {
                this.autoscaling = false;
                start = [evt.clientX, evt.clientY];
                orig = this.viewport.copy();
                const pt = this.mouse_coordinates(evt);
                const alpha = clip((pt[0] - orig.left) / orig.width, 0, 1);
                mid = orig.left + alpha * orig.width;
            },
            evt => {
                // Affine image transformation with `mid` as "focal point"
                const end = [evt.clientX, evt.clientY];
                const delta = subtract_arrays(end, start);
                const shift = -delta[0] / this.canvas.width * orig.width;
                const factor = Math.exp(-0.01 * delta[1]);
                this.viewport.left = factor * (orig.left - mid + shift) + mid;
                this.viewport.right = factor * (orig.right - mid + shift) + mid;
                this.update_transformation_matrices();
                this.draw();
            },
            () => {
                start = null;
                orig = null;
                mid = 0;
            },
            mouseButton,
            onShift,
        );
    }

    /**
     * Setup global key event listeners.
     */
    setup_keyboard_shortcuts() {
        addEventListener("keydown", evt => {
            switch(evt.key) {
                case "Backspace":
                    if (!this.selection.is_empty()) {
                        const knotNumbers = this.selection.sort();
                        this.selection.deselect_all();
                        this.remove_knots(this.foregroundCurve, this.foregroundChannel, knotNumbers);
                    }
                    break;
                case "ArrowLeft":
                    break;
                case "ArrowRight":
                    break;
                case "ArrowUp":
                    evt.preventDefault();
                    break;
                case "ArrowDown":
                    evt.preventDefault();
                    break;
                case "Shift":
                    this.svg.style.cursor = "move";
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
     * Emit custom curvechanging event.
     *
     * @param {Array} position Optional position value to trigger live preview.
     */
    emit_curve_changing(position=null) {
        emit_custom_event(this, "curvechanging", {
            position: position,
        })
    }

    /**
     * Emit custom curvechanged event.
     *
     * @param {Curve} newCurve New final curve.
     */
    emit_curve_changed(newCurve) {
        emit_custom_event(this, "curvechanged", {
            newCurve: newCurve,
        })
    }

    /**
     * Emit custom channelchanged event. When user clicks on another channel of
     * the foreground curve.
     *
     * @param {Number} channel Channel number.
     */
    emit_channel_changed(channel) {
        emit_custom_event(this, "channelchanged", {
            channel: channel,
        });
    }

    /**
     * Position annotation label around.
     *
     * @param {Array} pos Position to move to (data space).
     * @param {String} loc Location label identifier.
     * @param {Number} offset Offset value.
     */
    position_annotation(pos, loc = "ur", offset = 10) {
        const pt = this.transform_point(pos);
        let [x, y] = pt;
        const bbox = this.annotation.getBoundingClientRect();
        if (loc.endsWith("l")) {
            x -= bbox.width + offset;
        } else {
            x += offset;
        }

        if (loc.startsWith("u")) {
            y -= bbox.height + offset;
        } else {
            y += offset;
        }

        this.annotation.style.left = x + "px";
        this.annotation.style.top = y + "px";
    }

    /**
     * Make something draggable inside data space. Wraps default
     * make_draggable. Handles mouse -> image space -> data space
     * transformation, calculates delta offset, triggers redraws. Mostly used
     * to drag SVG elements around.
     *
     * @param {Element} ele Element to make draggable.
     * @param {Curve} curve working copy of the curve.
     * @param {Number} channel Active curve channel number.
     * @param {Function} on_drag On drag motion callback. Will be called with a relative
     * delta array.
     * @param {String} labelLocation Label location identifier.
     */
    make_draggable(ele, curve, channel, on_drag, labelLocation = "ur", start_drag=(evt, pos) => {}) {
        /** Start position of drag motion. */
        const spline = curve.splines[channel];
        let startPos = null;
        let yValues = [];

        make_draggable(
            ele,
            evt => {
                startPos = this.mouse_coordinates(evt);
                yValues = new Set(spline.c.flat(COEFFICIENTS_DEPTH));
                yValues.add(0.0);
                this.emit_curve_changing()
                if (ele.parentNode) {
                    ele.parentNode.classList.add("fade-in");
                }

                start_drag(evt, startPos);
            },
            evt => {
                let pos = this.mouse_coordinates(evt);
                pos = clip_point(pos, this.limits);
                if (this.snapping_to_grid & !evt.shiftKey) {
                    pos[1] = snap_to_value(pos[1], yValues, 0.001);
                }

                on_drag(pos);
                spline.restrict_to_bbox(this.limits);
                this.annotation.style.visibility = "visible";
                this.position_annotation(pos, labelLocation);
                this._draw_curve_elements();
            },
            evt => {
                const endPos = this.mouse_coordinates(evt);
                if (arrays_equal(startPos, endPos)) {
                    return;
                }

                this.emit_curve_changed(curve)
                this.annotation.style.visibility = "hidden";
                startPos = null;
                clear_array(yValues);
                if (ele.parentNode) {
                    ele.parentNode.classList.remove("fade-in");
                }
            }
        );
    }

    /**
     * Initialize an SVG path element and adds it to the SVG parent element.
     * data_source callback needs to deliver the 2-4 Bézier control points.
     *
     * @param {Function} data_source Callable data source returning the control points.
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
     * @param {Function} data_source Callable data source returning the center point.
     * @param {Number} radius Circle radius.
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
     * @param {function} data_source Callable data source which spits out the
     * current start and end point of the line.
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
     * Plot spline path of curve. This is non-interactive.
     *
     * @param {Curve} curve Curve to draw path for.
     * @param {Number} channel Active curve channel number.
     * @param {String} className CSS class name to assigne to path.
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
                path.classList.add("pointed");
                path.addEventListener("click", evt => {
                    evt.stopPropagation();  // Prevents transport cursor to jump
                    this.emit_channel_changed(channel);
                });
            }
        });
    }

    /**
     * Plot interactive control points with helper lines of spline.
     *
     * @param {Curve} curve Curve to draw control points / helper lines for.
     * @param {Number} channel Active curve channel number.
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
            this.make_draggable(
                controlPoint,
                curve,
                channel,
                pos => {
                    spline.position_control_point(knotNr, FIRST_CP, pos[1], this.c1);
                    const slope = spline.get_derivative_at_knot(knotNr, RIGHT);
                    this.annotation.innerHTML = "Slope: " + format_number(slope);
                },
            );
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
            this.make_draggable(
                controlPoint,
                curve,
                channel,
                pos => {
                    spline.position_control_point(knotNr - 1, SECOND_CP, pos[1], this.c1);
                    const slope = spline.get_derivative_at_knot(knotNr, LEFT);
                    this.annotation.innerHTML = "Slope: " + format_number(slope);
                },
            );
        }

        return cpGroup;
    }

    /**
     * Remove knots from curve channel spline.
     *
     * @param {Curve} curve Curve in question.
     * @param {Number} channel Spline number.
     * @param {Array} knotNumbers Knut indices to remove.
     */
    remove_knots(curve, channel, knotNumbers) {
        const wc = curve.copy()
        const spline = wc.splines[channel];
        if (spline.n_segments <= 1) {
            return;
        }

        this.emit_curve_changing();
        knotNumbers.sort().forEach((nr, i) => {
            if (spline.n_segments > 1) {
                spline.remove_knot(nr - i);
            }
        });
        this.emit_curve_changed(wc);
    }

    move_selected_knots(offset) {
    }

    /**
     * Plot interactive spline knots.
     *
     * @param {Curve} curve Curve to draw knots from.
     * @param {Number} channel Active curve channel number.
     * @param {Number} knotNr Knot number.
     * @param {Number} radius Radius of knot circle.
     * @returns {SVGCircleElement} Circle knot.
     */
    plot_knot(curve, channel, knotNr, radius) {
        const spline = curve.splines[channel];
        const knotCircle = this.create_svg_circle(() => spline.point(knotNr, KNOT), radius);
        this.foregroundKnotElements.push(knotCircle);
        knotCircle.classList.add("knot");

        let start = null;
        let initialPositions = [];
        let selectedKnotNumbers = [];

        /**
         * Select this knot. If shift is pressed add it to selection in any
         * case. If not deselect all before adding.
         */
        const click_select_this_knot = (evt) => {
            const nothingSelected = !this.selection.is_empty();
            const knotUnselected = !this.selection.is_selected(knotNr);
            if (nothingSelected && knotUnselected && !evt.shiftKey) {
                this.selection.deselect_all();
            }

            this.selection.select(knotNr);
            this.update_selected_elements();
        }

        this.make_draggable(
            knotCircle,
            curve,
            channel,
            pos => {
                this.emit_curve_changing(pos)
                const offset = subtract_arrays(pos, start);
                this.selection.sort().forEach((knotNr, i) => {
                    const target = add_arrays(initialPositions[i], offset);
                    spline.position_knot(knotNr, target, this.c1);
                });
                 
                const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                this.annotation.innerHTML = txt;
            },
            knotNr < spline.n_segments ? "ur" : "ul",
            (evt, startPos) => {
                start = startPos;
                clear_array(initialPositions);

                click_select_this_knot(evt);

                this.selection.sort().forEach(kn => {
                    initialPositions.push(spline.point(kn, KNOT))
                });
            },
        );
        knotCircle.addEventListener("click", evt => {
            click_select_this_knot(evt);
            evt.stopPropagation();
        });
        knotCircle.addEventListener("dblclick", evt => {
            this.selection.deselect_all();
            evt.stopPropagation();
            this.remove_knots(curve, channel, [knotNr]);
        });
        return knotCircle;
    }

    /**
     * Plot single curve channel.
     *
     * @param {Curve} curve Curve to plot.
     * @param {Number} channel Active curve channel number.
     * @param {String} className CSS class name to assigne to path.
     * @param {Number} radius Circle radius.
     */
    plot_curve_channel(curve, channel, className, radius=6) {
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

            //this.selector.set_spline(spline);
            //this.selector.set_knot_circles(knotCircles);
        }
    }

    /**
     * Draw background curve.
     *
     * @param {Curve} curve Background curve to draw.
     */
    draw_background_curve(curve) {
        if (curve.n_splines === 0) {
            return;
        }
        curve.splines.forEach((spline, c) => {
            this.plot_curve_channel(curve, c, "background");
        });
        this._draw_curve_elements();
    }

    /**
     * Draw foreground curve. Selected channel will be interactive.
     *
     * @param {Curve} curve Foreground curve to draw.
     */
    draw_foreground_curve(curve, channel=-1) {
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
            this.foregroundCurve = curve;
            this.foregroundChannel = channel;
            this.update_selected_elements();
        }

        this._draw_curve_elements();
    }

    /**
     * Draw / update all SVG elements.
     */
    _draw_curve_elements() {
        this.otherElements.forEach(ele => ele.draw());
        this.foregroundPathElements.forEach(ele => ele.draw());
        this.foregroundKnotElements.forEach(ele => ele.draw());
    }

    /**
     * Draw the current state (update all SVG elements).
     */
    draw() {
        super.draw();
        this._draw_curve_elements();
    }
}


customElements.define("being-drawer", Drawer);
