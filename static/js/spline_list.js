"use strict";
import { remove_all_children, fetch_json } from "/static/js/utils.js";
import { BPoly } from "/static/js/spline.js";
import { HTTP_HOST } from "/static/js/constants.js";

export class SplineList {
    constructor(editor) {
        this.editor = editor
        this.splines = []
        this.visibles = new Set()
        this.selected = null

        this.add_spline_list()
    }

    /**
     * Build node and attach to parent (editor)
     */
    add_spline_list() {
        const container = document.createElement("div")
        container.classList.add("spline-list")

        const title = document.createElement("h2")
        title.appendChild(document.createTextNode("Motions"))
        container.appendChild(title)

        this.splineListDiv = document.createElement("div")
        this.splineListDiv.style.borderBottom = "2px solid black"
        this.splineListDiv.style.paddingBottom = "5px"
        container.appendChild(this.splineListDiv)

        const newBtnContainer = document.createElement("div")
        container.appendChild(newBtnContainer)
        newBtnContainer.style.display = "flex"
        newBtnContainer.style.justifyContent = "center"

        this.addSplineButton = this.editor.add_button("add_box", "Create new spline")
        this.addSplineButton.addEventListener("click", evt => {
            this.create_spline().then(res => {
                this.fetch_splines().then(() =>
                    this.update_spline_list()
                )
            })
        });
        newBtnContainer.appendChild(this.addSplineButton)


        this.delSplineButton = this.editor.add_button("delete", "Delete selected motion")
        this.delSplineButton.addEventListener("click", evt => {
            this.delete_spline().then(res => {
                this.fetch_splines().then(() =>
                    this.update_spline_list()
                )
            })
        });
        newBtnContainer.appendChild(this.delSplineButton)

        this.duplSplineButton = this.editor.add_button("file_copy", "Duplicate motion file")
        this.duplSplineButton.addEventListener("click", evt => {
            this.duplicate_spline(this.selected).then(() => {
                this.fetch_splines().then(() =>
                    this.update_spline_list()
                )
            })
        })
        newBtnContainer.appendChild(this.duplSplineButton)


        // insert after css link
        this.editor.shadowRoot.insertBefore(container, this.editor.shadowRoot.childNodes[1])
    }


    async fetch_splines() {
        try {
            return await fetch_json("/api/motions").then(res => {
                this.splines = res
                this.splines.forEach(spline => {
                    spline.content = BPoly.from_object(spline.content)
                })
            })
        }
        catch (err) {
            throw Error(err)
        }
    }

    update_spline_list() {

        remove_all_children(this.splineListDiv)

        this.splines.forEach(spline => {
            const entry = document.createElement("div")
            entry.classList.add("spline-list-entry")
            entry.classList.add("noselect")
            entry.id = spline.filename
            entry.addEventListener("click", evt => {
                if (evt.currentTarget.id !== this.selected) {
                    // Cant unselect current spline, at least one spline needs 
                    // to be selected. 
                    this.selected = evt.currentTarget.id
                    this.visibles.add(evt.currentTarget.id)
                    this.update_spline_list_selection()
                    this.init_spline_selection()
                    const selectedSpline = this.splines.filter(sp => sp.filename === this.selected)[0]
                    this.editor.load_spline(selectedSpline.content)
                    this.draw_background_splines()
                }
            });

            const checkbox = document.createElement("span")
            checkbox.classList.add("spline-checkbox")
            checkbox.classList.add("material-icons")
            checkbox.classList.add("mdc-icon-button")
            checkbox.innerHTML = ""
            checkbox.value = spline.filename
            checkbox.title = "Show in Graph"
            checkbox.addEventListener("click", evt => {
                evt.stopPropagation()
                const filename = evt.target.parentNode.id
                if (this.selected === filename) {
                    return
                }

                if (this.visibles.has(filename)) {
                    this.visibles.delete(filename)
                }
                else {
                    this.visibles.add(filename)
                }
                this.update_spline_list_selection()
                this.draw_background_splines()
            }, true)
            checkbox.addEventListener("mouseover", evt => {
                evt.stopPropagation()
                evt.currentTarget.innerHTML = "visibility"
            })
            checkbox.addEventListener("mouseout", evt => {
                const filename = evt.target.parentNode.id
                if (!this.visibles.has(filename)) {
                    evt.currentTarget.innerHTML = ""
                }
            })

            const text = document.createElement("span")
            text.innerHTML = spline.filename
            text.contentEditable = "false" // "false" prevents text syntax highlighting
            text.title = "Double click to edit"
            entry.append(checkbox, text)
            text.addEventListener("blur", evt => {
                let current_elem = evt.currentTarget
                evt.currentTarget.contentEditable = "false"
                if (this.origFilename !== evt.currentTarget.innerHTML) {
                    const newFilename = evt.currentTarget.innerHTML
                    if (newFilename.length <= 0 ||
                        newFilename === "<br>" ||
                        newFilename === "<p>" ||
                        newFilename === "<div>") {
                        evt.currentTarget.innerHTML = this.origFilename
                    } else {
                        this.rename_spline(this.origFilename, newFilename).then(res => {
                            // local update
                            // We dont want to reload from the server because we want to keep the 
                            // evenetually modified spline and history when renaming
                            let spl = this.splines.filter(sp => sp.filename === this.origFilename)[0]
                            spl.filename = newFilename

                            if (this.selected === this.origFilename) {
                                this.selected = newFilename
                            }

                            if (this.visibles.has(this.origFilename)) {
                                this.visibles.delete(this.origFilename)
                                this.visibles.add(newFilename)
                            }

                            const filename_div = this.editor.shadowRoot.getElementById(this.origFilename)
                            filename_div.id = newFilename

                            console.log("renamed!!")
                        }).catch(() => {
                            // same filename exists
                            current_elem.innerHTML = this.origFilename
                        })

                    }
                }
            })
            text.addEventListener("keyup", evt => {
                // Keyup eventListener needed to capture meta keys
                if (evt.key === "Escape") {
                    evt.currentTarget.innerHTML = this.origFilename
                    evt.currentTarget.blur() // saving file handled by "blur" eventListener
                }
            })
            text.addEventListener("dblclick", evt => {
                if (!evt.currentTarget.isContentEditable) {
                    evt.currentTarget.contentEditable = "true"
                    evt.currentTarget.focus()
                    this.origFilename = evt.currentTarget.innerHTML
                }
            })
            text.addEventListener("keypress", evt => {
                // Keypress eventListener (compared to keyup) fires before contenteditable adds <br>
                if (evt.key === "Enter") {
                    evt.currentTarget.blur() // saving file handled by "blur" eventListener
                }
            })


            this.splineListDiv.append(entry)

        })
        this.update_spline_list_selection()
        this.draw_background_splines()
    }


    draw_background_splines() {
        this.editor.backgroundDrawer.clear()

        let background_splines = this.splines.filter(sp => {
            return (this.visibles.has(sp.filename) && sp.filename !== this.selected)
        })

        for (let index in background_splines) {
            const spline_to_draw = background_splines[index].content
            this.editor.backgroundDrawer.draw_spline(spline_to_draw, false)
        }

        this.editor.backgroundDrawer.draw()
    }

    update_spline_list_selection() {
        let entries = this.editor.shadowRoot.querySelectorAll(".spline-list-entry")
        entries.forEach(entry => {
            entry.removeAttribute("checked")
            entry.querySelector(".spline-checkbox").innerHTML = ""
        })

        // Preselection 
        if (this.selected == null) {
            const latest = this.splines.length - 1
            if (latest >= 0) {
                const spline_fd = this.splines[latest].filename
                this.selected = spline_fd
                this.visibles.add(spline_fd)
            }
            this.init_spline_selection()
        }

        this.editor.shadowRoot.getElementById(this.selected).setAttribute("checked", "")
        this.visibles.forEach(filename => {
            const parent = this.editor.shadowRoot.getElementById(filename)
            const checkbox = parent.querySelector(".spline-checkbox")
            checkbox.innerHTML = "visibility";
        })
    }


    init_spline_selection() {
        this.editor.history.clear()
        const selectedSpline = this.splines.filter(sp => sp.filename === this.selected)[0]
        this.editor.history.capture(selectedSpline.content);
        const currentSpline = this.editor.history.retrieve();
        const bbox = currentSpline.bbox();
        bbox.expand_by_point([0., 0]);
        bbox.expand_by_point([0., .04]);
        this.dataBbox = bbox;
        this.viewport = this.dataBbox.copy();
    }


    /**
    * Create a new spline on the backend. Content is a line with 
    * arbitrary filename
    */
    async create_spline() {
        const url = HTTP_HOST + "/api/motions";
        const resp = await fetch(url, { method: "POST" });

        return await resp.json()
    }

    async delete_spline() {
        // TODO: Ask user only the first time he deletes a file?
        // Replace ugly confirm dialog
        if (confirm("Delete motion " + this.selected + " permanently ?")) {
            const url = HTTP_HOST + "/api/motions/" + this.selected;
            const resp = await fetch(url, { method: "DELETE" });

            if (resp.ok) {
                this.visibles.delete(this.selected)
                this.selected = null
                return true
            }
        }
    }

    async rename_spline(name, new_name) {
        const url = HTTP_HOST + "/api/motions/" + name + "?rename=" + new_name;
        const resp = await fetch(url, { method: "PUT" });

        return await resp.json()
    }

    async duplicate_spline(name) {
        const url = HTTP_HOST + "/api/motions/" + name;
        const resp = await fetch(url, { method: "POST" });

        return true
    }
}
