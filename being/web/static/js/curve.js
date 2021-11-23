import { array_min, array_max } from "/static/js/array.js";
import { BBox } from "/static/js/bbox.js";
import { BPoly } from "/static/js/spline.js";


export const ALL_CHANNELS = new Object()


/**
 * Curve set container.
 */
export class Curve {
    constructor(splines) {
        this.splines = splines;
    }

    get start() {
        if (this.n_splines === 0) {
            return 0.0;
        }

        return array_min(this.splines.map(s => {
            return s.start;
        }));
    }

    get end() {
        if (this.n_splines === 0) {
            return 0.0;
        }

        return array_max(this.splines.map(s => {
            return s.end;
        }));
    }

    get duration() {
        return this.end;
    }

    get n_splines() {
        return this.splines.length;
    }

    get n_channels() {
        return this.splines.reduce((nChannels, spline) => {
            return nChannels + spline.ndim;
        }, 0);
    }

    bbox() {
        const bbox = new BBox();
        this.splines.forEach(s => {
            bbox.expand_by_bbox(s.bbox());
        });
        return bbox;
    }

    restrict_to_bbox(bbox) {
        this.splines.forEach(spline => {
            spline.restrict_to_bbox(bbox);
        });
    }

    copy() {
        return new Curve(this.splines.map(s => {
            return s.copy();
        }));
    }

    static from_dict(dct) {
        const splines = dct.splines.map(BPoly.from_dict);
        return new Curve(splines);
    }

    to_dict() {
        return {
            "type": "Curve",
            "splines": this.splines.map(s => {return s.to_dict();}),
        }
    }

    scale(factor, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.scale(factor));
        } else {
            this.splines[channel].scale(factor);
        }
    }

    stretch(factor, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.stretch(factor));
        } else {
            this.splines[channel].stretch(factor);
        }
    }

    shift(offset, channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.shift(offset));
        } else {
            this.splines[channel].shift(offset);
        }
    }

    flip_horizontally(channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.flip_horizontally());
        } else {
            this.splines[channel].flip_horizontally();
        }
    }

    flip_vertically(channel=ALL_CHANNELS) {
        if (channel === ALL_CHANNELS) {
            this.splines.forEach(s => s.flip_vertically());
        } else {
            this.splines[channel].flip_vertically();
        }
    }
};
