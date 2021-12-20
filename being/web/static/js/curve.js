/**
 * Curve container.
 * @module js/curve
 */
import { array_min, array_max } from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { BPoly } from "/static/js/spline.js";


/** @constant {object} - Targeting all channels literal. */
export const ALL_CHANNELS = new Object();


/**
 * Curve container. A curve contains multiple individual splines (channels).
 * @param {array} splines - Individual curve splines.
 */
export class Curve {
    constructor(splines) {
        this.splines = splines;
    }

    /**
     * Get start time of curve.
     * @type {number}
     */
    get start() {
        if (this.n_splines === 0) {
            return 0.0;
        }

        return array_min(this.splines.map(s => {
            return s.start;
        }));
    }

    /**
     * Get end time of curve.
     * @type {number}
     */
    get end() {
        if (this.n_splines === 0) {
            return 0.0;
        }

        return array_max(this.splines.map(s => {
            return s.end;
        }));
    }

    /**
     * Get curve duration. Initial delay is not considered.
     * @type {number}
     */
    get duration() {
        return this.end;
    }

    /**
     * Get number of splines.
     * @type {number}
     */
    get n_splines() {
        return this.splines.length;
    }

    /**
     * Get number of channels.
     * @type {number}
     */
    get n_channels() {
        return this.splines.reduce((nChannels, spline) => {
            return nChannels + spline.ndim;
        }, 0);
    }

    /**
     * Calculate bounding box of curve.
     */
    bbox() {
        const bbox = new BBox();
        this.splines.forEach(s => {
            bbox.expand_by_bbox(s.bbox());
        });
        return bbox;
    }

    /**
     * Restrict curve to bounding box (in place).
     * @param {BBox} bbox - Restricting bounding box.
     */
    restrict_to_bbox(bbox) {
        this.splines.forEach(spline => {
            spline.restrict_to_bbox(bbox);
        });
    }

    /**
     * Copy curve.
     * @returns {Curve} - New curve copy.
     */
    copy() {
        return new Curve(this.splines.map(s => {
            return s.copy();
        }));
    }

    /**
     * Build curve from JSON object (deserialization). No checks are performed.
     * @param {object} dct - JSON object.
     * @returns {Curve} - Deserialized curve instance.
     */
    static from_dict(dct) {
        const splines = dct.splines.map(BPoly.from_dict);
        return new Curve(splines);
    }

    /**
     * Convert curve to JSON object representation (for serialization).
     * @returns {object} - JSON object.
     */
    to_dict() {
        return {
            "type": "Curve",
            "splines": this.splines.map(s => {return s.to_dict();}),
        }
    }

    /**
     * Scale curve position values by some factor (in place).
     * @param {number} factor - Scale factor.
     * @param {number} [channel=ALL_CHANNELS] - Target channel.
     */
    scale(factor, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.scale(factor));
        } else {
            this.splines[channel].scale(factor);
        }
    }

    /**
     * Stretch curve in time by some factor (in place).
     * @param {number} factor - Scale factor.
     * @param {number} [channel=ALL_CHANNELS] - Target channel.
     */
    stretch(factor, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.stretch(factor));
        } else {
            this.splines[channel].stretch(factor);
        }
    }

    /**
     * Shift curve in time by some offset (in place).
     * @param {number} offset - Shift offset.
     * @param {number} [channel=ALL_CHANNELS] - Target channel.
     */
    shift(offset, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.shift(offset));
        } else {
            this.splines[channel].shift(offset);
        }
    }

    /**
     * Flip curve horizontally in time (in place).
     * @param {number} [channel=ALL_CHANNELS] - Target channel.
     */
    flip_horizontally(channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.flip_horizontally());
        } else {
            this.splines[channel].flip_horizontally();
        }
    }

    /**
     * Flip curve vertically in time (in place).
     * @param {number} [channel=ALL_CHANNELS] - Target channel.
     */
    flip_vertically(channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.flip_vertically());
        } else {
            this.splines[channel].flip_vertically();
        }
    }
};
