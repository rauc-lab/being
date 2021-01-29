"use strict";
import {create_element, path_d, draw_path, draw_circle, draw_line} from '/static/js/svg.js';
import {remove_all_children} from '/static/js/utils.js';


const LINE_WIDTH = .1;
const QUADRATIC = 2;
const CUBIC = 3;
const EXAMPLE_DATA = [
    [
        [0.0, 0.0],
        [0.3333333333333333, 0.6039136302294198],
        [0.6666666666666666, 0.902609086819613],
        [1.0, 1.0],
    ], [
        [1.0, 1.0],
        [1.6666666666666665, 1.1947818263607737],
        [2.333333333333333, 0.5843454790823213],
        [3.0, 2.220446049250313e-16],
    ], [
        [3.0, 0.0],
        [4.333333333333333, -1.1686909581646423],
        [5.666666666666666, -2.2330184435447595],
        [7.0, -1.9999999999999996],
    ], [
        [7.0, -2.0],
        [7.666666666666667, -1.8834907782276202],
        [8.333333333333334, -1.4426450742240213],
        [9.0, 0.0],
    ], [
        [9.0, 0.0],
        [9.333333333333334, 0.7213225371120107],
        [9.666666666666666, 1.693094916779127],
        [10.0, 3.0],
    ]
];
const DEFAULT_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2',
    '#7f7f7f', '#bcbd22', '#17becf',
];


/**
 * Dummy spline editor for demonstrating how to work with Bézier control point
 * format.
 */
function SplineEditor(svg) {
    svg.setAttribute("viewBox", "-1 -4 12 10");
    remove_all_children(svg);
    EXAMPLE_DATA.forEach(function(cps, i) {
        const lw = LINE_WIDTH;

        // Draw path and knots
        const color = DEFAULT_COLORS[i % DEFAULT_COLORS.length];
        draw_path(svg, cps, lw, color);
        const last = cps.length - 1
        draw_circle(svg, cps[0], 2*lw, color);
        draw_circle(svg, cps[last], 2*lw, color);

        // Draw control points and lines
        const order = cps.length;
        const degree = order - 1
        if (degree == QUADRATIC) {
            draw_line(svg, cps[0], cps[1], .5*lw, 'black');
            draw_circle(svg, cps[1], lw, 'red');

        } else if (degree == CUBIC) {
            draw_line(svg, cps[0], cps[1], .5*lw, 'black');
            draw_line(svg, cps[2], cps[3], .5*lw, 'black');
            draw_circle(svg, cps[1], lw, 'red');
            draw_circle(svg, cps[2], lw, 'red');
        }
    })
}

export {SplineEditor};
