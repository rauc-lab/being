/**
 * @module layout Graphical layout helpers. Only finding nice tick labels for now. Taken from here:
 *     https://stackoverflow.com/questions/8506881/nice-label-algorithm-for-charts-with-minimum-ticks/16363437
 */


/**
 * Find nice number for data range.
 * @param {number} range Data space width.
 * @param {boolean} round Perform number rounding.
 * @returns {number} Nice number.
 */
export function nice_number(range, round = false) {
    const exponent = Math.floor(Math.log10(range));
    const fraction = range / Math.pow(10, exponent);
    let niceFraction;
    if (round) {
        if (fraction < 1.5)
            niceFraction = 1;
        else if (fraction < 3)
            niceFraction = 2;
        else if (fraction < 7)
            niceFraction = 5;
        else
            niceFraction = 10;
    } else {
        if (fraction <= 1)
            niceFraction = 1;
        else if (fraction <= 2)
            niceFraction = 2;
        else if (fraction <= 5)
            niceFraction = 5;
        else
            niceFraction = 10;
    }

    return niceFraction * Math.pow(10, exponent);
}


/**
 * Nice tick numbers for a given data range.
 * @param {number} lower Lower limit of data range.
 * @param {number} upper Upper limit of data range.
 * @param {number} maxTicks Maximum number of ticks.
 * @returns {array} Tick number candidates.
 */
export function tick_space(lower, upper, maxTicks=5) {
    const range = nice_number(upper - lower, false);
    const spacing = nice_number(range / (maxTicks - 1), true);
    const niceLower = Math.floor(lower / spacing) * spacing;
    //const niceUpper = Math.ceil(upper / spacing) * spacing;
    let span = [];
    for (let i=0; i<=maxTicks; i++) {
        span.push(Number((niceLower + i * spacing).toPrecision(4)));
    }

    return span;
}