"use strict";
import { BBox } from "/static/js/bbox.js";
import { make_draggable } from "/static/js/draggable.js";
import { arange } from "/static/js/math.js";
import { KNOT, FIRST_CP, SECOND_CP, Degree } from "/static/js/spline.js";
import { create_element, path_d, setattr } from "/static/js/svg.js";
import { assert, arrays_equal, clear_array } from "/static/js/utils.js";


export class SplineDrawer {
    constructor(editor, container) {
        this.editor = editor;
        this.container = container;
        this.splines = [];
        this.elements = [];
        this.c1 = true;
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
     * Make something draggable inside data space. Wraps default
     * make_draggable. Handles mouse -> image space -> data space
     * transformation, calculates delta offset, triggers redraws. Mostly used
     * to drag SVG elements around.
     *
     * @param ele Element to make draggable.
     * @param on_drag On drag motion callback. Will be called with a relative
     * delta array.
     */
    make_draggable(ele, on_drag, workingCopy) {
        /** Start position of drag motion. */
        let start = null;

        make_draggable(
            ele,
            evt => {
                start = this.editor.mouse_coordinates(evt);
                this.editor.spline_changing();
            },
            evt => {
                const end = this.editor.mouse_coordinates(evt);
                on_drag(end);
                this.draw();
            },
            evt => {
                const end = this.editor.mouse_coordinates(evt);
                if (arrays_equal(start, end)) {
                    return;
                }
                this.editor.spline_changed(workingCopy);
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

        // Knots
        const knots = arange(wc.n_segments + 1);
        knots.forEach(knot => {
            const circle = this.init_circle(() => {
                return wc.point(knot);
            }, 3 * lw);
            this.make_draggable(
                circle,
                pos => {
                    wc.position_knot(knot, pos, this.c1);
                },
                wc,
            );
            circle.addEventListener("dblclick", evt => {
                this.editor.spline_changing();
                evt.stopPropagation();
                wc.remove_knot(knot);
                this.editor.spline_changed(wc);
            });
        });


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
                        wc.position_control_point(seg, cp, pos[1], this.c1);
                    },
                    wc,
                );
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
