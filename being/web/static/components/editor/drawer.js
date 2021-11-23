/**
 * @module splien_drawer Component for drawing the actual splines inside the spline editor.
 */
import { arange, subtract_arrays } from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { make_draggable } from "/static/js/draggable.js";
import { clip } from "/static/js/math.js";
import { Plotter } from "/static/components/plotter.js";
import { COEFFICIENTS_DEPTH, KNOT, FIRST_CP, SECOND_CP, Degree, LEFT, RIGHT } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import { assert, arrays_equal, clear_array, remove_all_children, emit_custom_event } from "/static/js/utils.js";


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
    cursor: move;
}

.pointed {
    cursor: pointer;
}

circle {
    cursor: pointer;
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
}

.control-point line {
    stroke: black;
}

.control-point circle {
    fill: red;
}

.fade-in {
    opacity: 1.0 !important;
    transition: none;
}

.control-point {
    opacity: 0.1;
    transition: opacity 1.0s ease-out 0.5s;
}

.control-point:hover {
    opacity: 1.0;
    transition: none;
}

.knot:hover + .control-point {
    opacity: 1.0;
    transition: none;
}
</style>
`


export class Drawer extends Plotter {
    constructor() {
        super();
        this.append_template(EXTRA_STYLE);
        this.annotation = document.createElement("span");
        this.annotation.classList.add("annotation");
        this.shadowRoot.appendChild(this.annotation);
        this.autoscaling = false;

        this.container = this.svg.appendChild(create_element("g"));
        this.elements = [];
        this.c1 = true;
        this.snapping_to_grid = true;
        this.limits = new BBox([0, -Infinity], [Infinity, Infinity]);

        this.setup_svg_drag_navigation();
    }

    /**
     * Clear everything.
     */
    clear() {
        clear_array(this.elements);
        remove_all_children(this.container);
    }

    /**
     * Setup drag event handlers for moving horizontally and zooming
     * vertically.
     */
    setup_svg_drag_navigation() {
        let start = null;
        let orig = null;
        let mid = 0;

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
        );
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
    make_draggable(ele, curve, channel, on_drag, labelLocation = "ur") {
        /** Start position of drag motion. */
        const spline = curve.splines[channel];
        let start = null;
        let yValues = [];

        make_draggable(
            ele,
            evt => {
                start = this.mouse_coordinates(evt);
                yValues = new Set(spline.c.flat(COEFFICIENTS_DEPTH));
                yValues.add(0.0);
                this.emit_curve_changing()
                if (ele.parentNode) {
                    ele.parentNode.classList.add("fade-in");
                }
            },
            evt => {
                let end = this.mouse_coordinates(evt);
                end = clip_point(end, this.limits);
                if (this.snapping_to_grid & !evt.shiftKey) {
                    end[1] = snap_to_value(end[1], yValues, 0.001);
                }

                on_drag(end);
                spline.restrict_to_bbox(this.limits);
                this.annotation.style.visibility = "visible";
                this.position_annotation(end, labelLocation);
                this._draw_curve_elements();
            },
            evt => {
                const end = this.mouse_coordinates(evt);
                if (arrays_equal(start, end)) {
                    return;
                }

                this.emit_curve_changed(curve)
                this.annotation.style.visibility = "hidden";
                start = null;
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
    add_svg_path(data_source) {
        const path = create_element("path");
        this.elements.push(path);
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
    add_svg_circle(data_source, radius) {
        const circle = create_element("circle");
        setattr(circle, "r", radius);
        this.elements.push(circle);
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
    add_svg_line(data_source) {
        const line = create_element("line");
        this.elements.push(line);
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
            const path = this.add_svg_path(() => [
                spline.point(seg, 0),
                spline.point(seg, 1),
                spline.point(seg, 2),
                spline.point(seg + 1, 0),
            ]);
            this.container.appendChild(path);
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
        const knotCircle = this.add_svg_circle(() => spline.point(knotNr, 0), radius);
        knotCircle.classList.add("knot");
        this.make_draggable(
            knotCircle,
            curve,
            channel,
            pos => {
                this.emit_curve_changing(pos)
                spline.position_knot(knotNr, pos, this.c1);
                const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                this.annotation.innerHTML = txt;
            },
            knotNr < spline.n_segments ? "ur" : "ul",
        );
        knotCircle.addEventListener("dblclick", evt => {
            evt.stopPropagation();
            if (spline.n_segments > 1) {
                this.emit_curve_changing();
                const wc = curve.copy();
                wc.splines[channel].remove_knot(knotNr);
                this.emit_curve_changed(wc);
            }
        });
        return knotCircle;
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
        const group = create_element("g");
        if (knotNr < spline.n_segments) {
            // Right helper line
            const helperLine = this.add_svg_line(() => [
                spline.point(knotNr, KNOT),
                spline.point(knotNr, FIRST_CP),
            ]);
            group.appendChild(helperLine);

            // Right control point
            const controlPoint = this.add_svg_circle(() => spline.point(knotNr, FIRST_CP), radius);
            group.appendChild(controlPoint);
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
            const helperLine = this.add_svg_line(() => [
                spline.point(knotNr, KNOT),
                spline.point(knotNr - 1, SECOND_CP),
            ]);
            group.appendChild(helperLine);

            // Left control point
            const controlPoint = this.add_svg_circle(() => spline.point(knotNr - 1, SECOND_CP), radius);
            group.appendChild(controlPoint);
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

        return group;
    }

    /**
     * Plot single curve channel.
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
            window.spline = spline;
            const knots = arange(spline.n_segments + 1);
            knots.forEach(knotNr => {
                // Plot knots
                const knotCircle = this.plot_knot(curve, channel, knotNr, radius);
                this.container.appendChild(knotCircle)


                // Plot control points and helper lines
                const group = this.plot_control_point(curve, channel, knotNr, radius)
                group.classList.add("control-point");
                this.container.appendChild(group);
            });
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
        }

        this._draw_curve_elements();
    }

    /**
     * Draw / update all SVG elements.
     */
    _draw_curve_elements() {
        this.elements.forEach(ele => ele.draw());
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
