/**
 * @module splien_drawer Component for drawing the actual splines inside the spline editor.
 */
import { BBox } from "/static/js/bbox.js";
import { make_draggable } from "/static/js/draggable.js";
import { arange, subtract_arrays } from "/static/js/array.js";
import { clip } from "/static/js/math.js";
import { COEFFICIENTS_DEPTH, KNOT, FIRST_CP, SECOND_CP, Degree, LEFT, RIGHT } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import { assert, arrays_equal, clear_array, remove_all_children } from "/static/js/utils.js";
import { Plotter } from "/static/components/plotter.js";


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
.annotation {
    position: absolute;
    visibility: hidden;
    box-shadow: 0 0 10px 10px rgba(255, 255, 255, .666);
    background-color: rgba(255, 255, 255, .666);
}
</style>
`


export class CurveDrawer extends Plotter {
    constructor() {
        super();
        this.autoscaling = false;
        this.splines = [];
        this.elements = [];
        this.container = this.svg.appendChild(create_element("g"));

        this.append_template(EXTRA_STYLE);
        this.annotation = document.createElement("span");
        this.annotation.classList.add("annotation");
        this.shadowRoot.appendChild(this.annotation);

        this.c1 = true;
        this.snapping_to_grid = true;
        this.limits = new BBox([0, -Infinity], [Infinity, Infinity]);

        this.setup_svg_drag_navigation();
    }

    /**
     * Clear everything from SplineDrawer.
     */
    clear() {
        remove_all_children(this.container);
        clear_array(this.splines);
        clear_array(this.elements);
    }

    /**
     * Calculate data bounding box of all drawn curves.
     */
    curves_bbox() {
        const bbox = new BBox();
        this.splines.forEach(spline => {
            bbox.expand_by_bbox(spline.bbox());
        });

        return bbox;
    }

    /**
     * Set vertical limits.
     */
    set_vertical_limits(ymin=-Infinity, ymax=Infinity) {
        console.log("Drawer.set_vertical_limits()", ymin, ymax);
        this.limits.ll[1] = ymin;
        this.limits.ur[1] = ymax;
        //this.viewport.ll[1] = Math.min(this.viewport.ll[1], ymin);
        //this.viewport.ur[1] = Math.max(this.viewport.ur[1], ymax);

        //this.update_transformation_matrices();
        //this.draw();
    }

    /**
     * Setup drag event handlers for moving horizontally and zooming vertically.
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
     */
    emit_curve_changing(position=null) {
        const evt = new CustomEvent("curvechanging", {
            detail: {
                position: position,
            }
        });
        this.dispatchEvent(evt)
    }


    /**
     * Emit custom curvechanged event.
     */
    emit_curve_changed(newCurve) {
        const evt = new CustomEvent("curvechanged", {
            detail: {
                newCurve: newCurve,
            }
        });
        this.dispatchEvent(evt)
    }

    /**
     * Position annotation label around.
     *
     * @param {Array} pos Position to move to (data space).
     * @param {String} location Label location identifier.
     */
    position_annotation(pos, location = "ur", offset=10) {
        const pt = this.transform_point(pos);
        let [x, y] = pt;
        const bbox = this.annotation.getBoundingClientRect();
        if (location.endsWith("l")) {
            x -= bbox.width + offset;
        } else {
            x += offset;
        }

        if (location.startsWith("u")) {
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
     * @param ele Element to make draggable.
     * @param on_drag On drag motion callback. Will be called with a relative
     * delta array.
     * @param labelLocation {String} Label location identifier.
     */
    make_draggable(ele, on_drag, workingCopy, labelLocation = "ur") {
        /** Start position of drag motion. */
        let start = null;
        let yValues = [];

        make_draggable(
            ele,
            evt => {
                start = this.mouse_coordinates(evt);
                yValues = new Set(workingCopy.c.flat(COEFFICIENTS_DEPTH));
                yValues.add(0.0);
                this.emit_curve_changing()
            },
            evt => {
                let end = this.mouse_coordinates(evt);
                end = clip_point(end, this.limits);
                if (this.snapping_to_grid & !evt.shiftKey) {
                    end[1] = snap_to_value(end[1], yValues, 0.001);
                }

                on_drag(end);
                workingCopy.restrict_to_bbox(this.limits);
                this.annotation.style.visibility = "visible";
                this.position_annotation(end, labelLocation);
                this.draw_curves();
            },
            evt => {
                const end = this.mouse_coordinates(evt);
                if (arrays_equal(start, end)) {
                    return;
                }

                this.emit_curve_changed(workingCopy)
                this.annotation.style.visibility = "hidden";
                start = null;
                clear_array(yValues);
            }
        );
    }

    /**
     * Initialize an SVG path element and adds it to the SVG parent element.
     * data_source callback needs to deliver the 2-4 Bézier control points.
     */
    add_svg_path(data_source, strokeWidth = 1, color = "black") {
        const path = create_element("path");
        setattr(path, "stroke", color);
        setattr(path, "stroke-width", strokeWidth);
        setattr(path, "fill", "transparent");
        this.container.appendChild(path);
        this.elements.push(path);
        path.draw = () => {
            setattr(path, "d", path_d(this.transform_points(data_source())));
        };

        return path;
    }

    /**
     * Initialize an SVG circle element and adds it to the SVG parent element.
     * data_source callback needs to deliver the center point of the circle.
     */
    add_svg_circle(data_source, radius = 1, color = "black") {
        const circle = create_element("circle");
        setattr(circle, "r", radius);
        setattr(circle, "fill", color);
        this.container.appendChild(circle);
        this.elements.push(circle);
        circle.draw = () => {
            const a = this.transform_point(data_source());
            setattr(circle, "cx", a[0]);
            setattr(circle, "cy", a[1]);
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
     * @param {Number} strokeWidth Stroke width of line.
     * @param {String} color Color string.
     * @returns SVG line instance.
     */
    add_svg_line(data_source, strokeWidth = 1, color = "black") {
        const line = create_element("line");
        setattr(line, "stroke-width", strokeWidth);
        setattr(line, "stroke", color);
        this.container.appendChild(line);
        this.elements.push(line);
        line.draw = () => {
            const [start, end] = data_source();
            const a = this.transform_point(start);
            const b = this.transform_point(end);
            setattr(line, "x1", a[0]);
            setattr(line, "y1", a[1]);
            setattr(line, "x2", b[0]);
            setattr(line, "y2", b[1]);
        };

        return line;
    }

    /**
     * Draw spline path / curve. This is non-interactive.
     *
     * @param {BPoly} spline Spline to draw curve / path.
     * @param {Number} lw Line width.
     * @param {Number} dim Which dimension to draw.
     */
    draw_curve(spline, lw = 1, dim = 0, color = "black") {
        const segments = arange(spline.n_segments);
        segments.forEach(seg => {
            this.add_svg_path(() => {
                return [
                    spline.point(seg, 0, dim),
                    spline.point(seg, 1, dim),
                    spline.point(seg, 2, dim),
                    spline.point(seg + 1, 0, dim),
                ];
            }, lw, color);
        });
    }

    /**
     * Draw interactive control points of spline.
     *
     * @param {BPoly} spline Spline to draw control points from.
     * @param {Number} lw Line width in pixel.
     * @param {Number} dim Which dimension to draw.
     */
    draw_control_points(spline, lw = 2, dim = 0) {
        const segments = arange(spline.n_segments);
        const cps = [];
        for (let cp=1; cp<spline.degree; cp++) {
            cps.push(cp);
        }

        segments.forEach(seg => {
            cps.forEach(cp => {
                // 1st helper line
                if (cp === FIRST_CP) {
                    this.add_svg_line(() => {
                        return [spline.point(seg, KNOT, dim), spline.point(seg, FIRST_CP, dim)];
                    });
                }

                // 2nd helper line
                if (spline.degree === Degree.QUADRATIC || cp === SECOND_CP) {
                    const rightKnot = KNOT + spline.degree;
                    this.add_svg_line(() => {
                        return [spline.point(seg, cp, dim), spline.point(seg, rightKnot, dim)];
                    });
                }

                // Control point
                const circle = this.add_svg_circle(() => {
                    return spline.point(seg, cp, dim);
                }, 3 * lw, "red");
                this.make_draggable(
                    circle,
                    pos => {
                        spline.position_control_point(seg, cp, pos[1], this.c1, dim);
                        let slope = 0;
                        if (cp === FIRST_CP) {
                            slope = spline.get_derivative_at_knot(seg, RIGHT, dim);
                        } else if (cp === SECOND_CP) {
                            slope = spline.get_derivative_at_knot(seg + 1, LEFT, dim);
                        }

                        this.annotation.innerHTML = "Slope: " + format_number(slope);
                    },
                    spline,
                );
            });
        });
    }

    /**
     * Draw interactive spline knots.
     *
     * @param {BPoly} spline Spline to draw knots from.
     * @param {Number} lw Line width in pixel.
     * @param {dim} dim Which dimension to draw.
     */
    draw_knots(spline, lw = 1, dim = 0) {
        const knots = arange(spline.n_segments + 1);
        knots.forEach(knot => {
            const circle = this.add_svg_circle(() => {
                return spline.point(knot, 0, dim);
            }, 3 * lw);
            this.make_draggable(
                circle,
                pos => {
                    this.emit_curve_changing(pos)
                    spline.position_knot(knot, pos, this.c1, dim);
                    const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                    this.annotation.innerHTML = txt;
                },
                spline,
                knot < spline.n_segments ? "ur" : "ul",
            );
            circle.addEventListener("dblclick", evt => {
                evt.stopPropagation();
                if (spline.n_segments > 1) {
                    this.emit_curve_changing();
                    spline.remove_knot(knot);
                    this.emit_curve_changed(spline);
                }
            });
        });
    }

    /**
     * Draw spline. Initializes SVG elements. If interactive also paint knots,
     * control points and helper lines and setup UI callbacks.
     */
    draw_spline(spline, interactive = true, channel = 0) {
        console.log("draw_spline()");
        console.log("spline.duration:", spline.duration);
        assert(spline.degree <= Degree.CUBIC, `Spline degree ${spline.degree} not supported!`);
        // Spline working copy
        const wc = spline.copy();
        this.splines.push(wc);
        const lw = interactive ? 2 : 1;
        arange(wc.ndim).forEach(dim => {
            const color = (dim === channel) ? "black" : "silver";
            this.draw_curve(wc, lw, dim, color);
            if (interactive && dim === channel) {
                this.draw_control_points(wc, lw, dim);
                this.draw_knots(wc, lw, dim);
            }
        });
        //this.draw();
    }

    draw_curves() {
        this.elements.forEach(ele => ele.draw());
    }

    /**
     * Draw the current state (update all SVG elements).
     */
    draw() {
        //console.log("Drawer.draw()")
        //console.log("viewport:", this.viewport.ll, this.viewport.ur)
        //const bbox = this.curves_bbox();
        //console.log("curves bbox:", bbox.ll, bbox.ur);
        //console.log('bbox:', bbox.ll, bbox.size)
        //this.viewport = bbox;
        //this.viewport.expand_by_bbox(bbox);
        //console.log(this.viewport.ll, this.viewport.size);
        // TODO
        //this.update_transformation_matrices();
        super.draw();
        this.draw_curves();
    }
}

customElements.define("being-curve-drawer", CurveDrawer);
