"use strict";
import { BBox } from "/static/js/bbox.js";
import { make_draggable } from "/static/js/draggable.js";
import { arange } from "/static/js/array.js";
import { clip } from "/static/js/math.js";
import { KNOT, FIRST_CP, SECOND_CP, Degree, LEFT, RIGHT } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import { assert, arrays_equal, clear_array } from "/static/js/utils.js";


/** Precision for label numbers */
const PRECISION = 3;


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
function format_number(number, smallest=1e-10) {
    if (Math.abs(number) < smallest) {
        return "0";
    }

    return number.toPrecision(PRECISION);
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


export class SplineDrawer {
    constructor(editor, container) {
        this.editor = editor;
        this.container = container;
        this.splines = [];
        this.elements = [];

        this.annotation = document.createElement("span");
        this.annotation.classList.add("annotation");
        editor.graph.appendChild(this.annotation);
    }


    /**
     * Calcualte data bounding box of drawn splines.
     */
    bbox() {
        const bbox = new BBox();
        this.splines.forEach(spline => {
            bbox.expand_by_bbox(spline.bbox());
        });

        return bbox;
    }


    /**
     * Clear everything from SplineDrawer.
     */
    clear() {
        while (this.container.hasChildNodes()) {
            this.container.removeChild(this.container.firstChild)
        }
        clear_array(this.splines);
        clear_array(this.elements);
    }


    /**
     * Position annotation label around.
     *
     * @param {Array} pos Position to move to (data space).
     * @param {String} location Label location identifier.
     */
    position_annotation(pos, location = "ur", offset=10) {
        const pt = this.editor.transform_point(pos);
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
        let limits = new BBox();

        make_draggable(
            ele,
            evt => {
                start = this.editor.mouse_coordinates(evt);
                yValues = new Set(workingCopy.c.flat());
                yValues.add(0.0);
                this.editor.spline_changing();
                limits = this.editor.limits();
            },
            evt => {
                let end = this.editor.mouse_coordinates(evt);
                end = clip_point(end, limits);
                if (this.editor.snapping_to_grid & !evt.shiftKey) {
                    end[1] = snap_to_value(end[1], yValues, 0.001);
                }

                on_drag(end);
                workingCopy.restrict_to_bbox(limits);
                this.annotation.style.visibility = "visible";
                this.position_annotation(end, labelLocation);
                this.draw();
            },
            evt => {
                const end = this.editor.mouse_coordinates(evt);
                if (arrays_equal(start, end)) {
                    return;
                }

                this.editor.spline_changed(workingCopy);
                this.annotation.style.visibility = "hidden";
                start = null;
                clear_array(yValues);
                limits.reset();
            }
        );
    }


    /**
     * Initialize an SVG path element and adds it to the SVG parent element.
     * data_source callback needs to deliver the 2-4 Bézier control points.
     */
    init_path(data_source, strokeWidth = 1, color = "black") {
        const path = create_element('path');
        setattr(path, "stroke", color);
        setattr(path, "stroke-width", strokeWidth);
        setattr(path, "fill", "transparent");
        this.container.appendChild(path)
        this.elements.push(path);
        path.draw = () => {
            setattr(path, "d", path_d(this.editor.transform_points(data_source())));
        };

        return path
    }


    /**
     * Initialize an SVG circle element and adds it to the SVG parent element.
     * data_source callback needs to deliver the center point of the circle.
     */
    init_circle(data_source, radius = 1, color = "black") {
        const circle = create_element('circle');
        setattr(circle, "r", radius);
        setattr(circle, "fill", color);
        this.container.appendChild(circle);
        this.elements.push(circle);
        circle.draw = () => {
            const a = this.editor.transform_point(data_source());
            setattr(circle, "cx", a[0]);
            setattr(circle, "cy", a[1]);
        };

        return circle;
    }


    /**
     * Initialize an SVG line element and adds it to the SVG parent element.
     * data_source callback needs to deliver the start end and point of the
     * line.
     */
    init_line(data_source, strokeWidth = 1, color = "black") {
        const line = create_element("line");
        setattr(line, "stroke-width", strokeWidth);
        setattr(line, "stroke", color);
        this.container.appendChild(line);
        this.elements.push(line);
        line.draw = () => {
            const [start, end] = data_source();
            const a = this.editor.transform_point(start);
            const b = this.editor.transform_point(end);
            setattr(line, "x1", a[0]);
            setattr(line, "y1", a[1]);
            setattr(line, "x2", b[0]);
            setattr(line, "y2", b[1]);
        };

        return line;
    }


    /**
     * Draw spline. Initializes SVG elements. If interactive also paint knots,
     * control points and helper lines and setup UI callbacks.
     */
    draw_spline(spline, interactive = true) {
        this.splines.push(spline);

        /** Spline working copy */
        const wc = spline.copy();
        const lw = interactive ? 2 : 1;

        // Path
        const segments = arange(wc.n_segments);
        segments.forEach(seg => {
            this.init_path(() => {
                return [
                    wc.point(seg, 0),
                    wc.point(seg, 1),
                    wc.point(seg, 2),
                    wc.point(seg + 1, 0),
                ];
            }, lw);
        });

        if (!interactive) {
            return;
        }

        // Control points
        assert(wc.degree <= Degree.CUBIC, "Spline degree not supported!");
        const cps = [];
        for (let cp=1; cp<wc.degree; cp++) {
            cps.push(cp);
        }

        segments.forEach(seg => {
            cps.forEach(cp => {
                // 1st helper line
                if (cp === FIRST_CP) {
                    this.init_line(() => {
                        return [wc.point(seg, KNOT), wc.point(seg, FIRST_CP)];
                    });
                }

                // 2nd helper line
                if (wc.degree === Degree.QUADRATIC || cp === SECOND_CP) {
                    const rightKnot = KNOT + wc.degree;
                    this.init_line(() => {
                        return [wc.point(seg, cp), wc.point(seg, rightKnot)];
                    });
                }

                // Control point
                const circle = this.init_circle(() => {
                    return wc.point(seg, cp);
                }, 3 * lw, "red");
                this.make_draggable(
                    circle,
                    pos => {
                        wc.position_control_point(seg, cp, pos[1], this.editor.c1);
                        let slope = 0;
                        if (cp === FIRST_CP) {
                            slope = wc.get_derivative_at_knot(seg, RIGHT);
                        } else if (cp === SECOND_CP) {
                            slope = wc.get_derivative_at_knot(seg + 1, LEFT);
                        }

                        this.annotation.innerHTML = "Slope: " + format_number(slope);
                    },
                    wc,
                );
            });
        });

        // Knots
        const knots = arange(wc.n_segments + 1);
        knots.forEach(knot => {
            const circle = this.init_circle(() => {
                return wc.point(knot);
            }, 3 * lw);
            this.make_draggable(
                circle,
                pos => {
                    this.editor.spline_changing(pos[1]);
                    wc.position_knot(knot, pos, this.editor.c1);
                    const txt = "Time: " + format_number(pos[0]) + "<br>Position: " + format_number(pos[1]);
                    this.annotation.innerHTML = txt;
                },
                wc,
                knot < wc.n_segments ? "ur" : "ul",
            );
            circle.addEventListener("dblclick", evt => {
                evt.stopPropagation();
                if (wc.n_segments > 1) {
                    this.editor.spline_changing();
                    wc.remove_knot(knot);
                    this.editor.spline_changed(wc);
                }
            });
        });

        this.draw();
    }


    /**
     * Draw the current state (update all SVG elements).
     */
    draw() {
        this.elements.forEach(ele => ele.draw());
    }
}
