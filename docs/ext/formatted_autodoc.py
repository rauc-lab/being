"""Quick and dirty custom extension for extending autodoc with custom field
formatters.

autodoc uses :func:`sphinx.util.inspect.object_description` for the value
representation. This boils down to :func:`repr` internally. But e.g. for
embedded register definitions :func:`hex` would be better suited.

Workaround: Overwriting :class:`sphinx.ext.autodoc.DataDocumenter` and
:class:`sphinx.ext.autodoc.AttributeDocumenter`. Looking for special role like
identifiers, popping most recently added line from current directive.result and
adding our own value representation.
"""
from sphinx.ext.autodoc import separate_metadata, Documenter, DataDocumenter, AttributeDocumenter


class FormattedDocumenter(Documenter):

    """Documenter mixin class with patched methods."""
    FORMATTERS = {
        ':bin:': bin,
        ':hex:': hex,
        ':str:': str,
        ':repr:': repr,
    }

    @staticmethod
    def filter_from_doc(doc, form):
        if not doc:
            return doc

        return [
            [s.replace(form, '').strip() for s in line]
            for line in doc
        ]

    def get_doc(self):
        doc = super().get_doc()
        for form in self.FORMATTERS:
            doc = self.filter_from_doc(doc, form)

        return doc

    def add_directive_header(self, sig):
        super().add_directive_header(sig)
        doc = super().get_doc()
        if not doc:
            return

        docstring, _ = separate_metadata('\n'.join(sum(doc, [])))
        sourcename = self.get_sourcename()
        for form, func in self.FORMATTERS.items():
            if form in docstring:
                self.directive.result.pop()
                self.add_line('   :value: ' + func(self.object), sourcename)
                break


BeingDataDocumenter = type('BeingDataDocumenter', (FormattedDocumenter, DataDocumenter), {})
BeingAttributeDocumenter = type('BeingAttributeDocumenter', (FormattedDocumenter, AttributeDocumenter), {})


def setup(app):
    app.setup_extension('sphinx.ext.autodoc')  # Require autodoc extension
    app.add_autodocumenter(BeingDataDocumenter, override=True)
    app.add_autodocumenter(BeingAttributeDocumenter, override=True)
