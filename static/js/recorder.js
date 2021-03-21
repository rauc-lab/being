import {clear_array} from "/static/js/utils.js";


export class Recorder {
    constructor() {
        this.trajectory = [];
        this.recording = false;
    }

    erase() {
        clear_array(this.trajectory);
    }

    process_sample(t, pos) {
        if (this.recording) {
            this.trajectory.push([t, pos]);
        }
    }

    record() {
        this.recording = true;
    }

    pause() {
        this.recording = false;
    }

    stop() {
        this.pause();
        this.erase();
    }
}