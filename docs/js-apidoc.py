"""Auto apidoc for JS."""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess


def assert_jsdoc():
    if shutil.which('jsdoc') is None:
        raise RuntimeError(
            'Could not locate jsdoc. This can be installed via npm with'
            '\n\n\tnpm install -g jsdoc'
        )


def analyze_js(*directories, recursive=True) -> list:
    """Analyze JS code inside directory."""
    assert_jsdoc()

    #cmd = f'jsdoc --recurse --explain {directory!r}'
    commands = ['jsdoc', '--explain']
    if recursive:
        commands.append('--recurse')

    commands.extend([ repr(os.path.normpath(d)) for d in directories ])
    cmd = ' '.join(commands)
    data = subprocess.getoutput(cmd)
    return json.loads(data)


def is_undocumented(doc):
    """Check if doclet is undocumented."""
    if doc.get('undocumented'):
        return True

    c = doc.get('comment', '')
    return len(c.strip()) == 0


def filter_doclets(doclets):
    """Filter doclets of interest."""
    seen = set()
    for doc in doclets:
        # Available kinds are ['class', 'function', 'constant', 'member',
        # 'module', 'package']
        if doc['kind'] not in [ 'module', 'constant', 'function', 'class' ]:
            continue

        if is_undocumented(doc):
            continue

        longname = doc['longname']

        if longname in seen:
            continue

        # Skip class methods
        if '#' in longname:
            continue

        # Skip whatever that is
        if '~' in longname:
            continue

        seen.add(longname)
        yield doc


def module_name(longname):
    """Full module name from longname."""
    if not 'module:' in longname:
        raise RuntimeError(f'Unknown module for {longname!r}!')

    fullname = longname.removeprefix('module:')
    modname = fullname.split('.', maxsplit=1)[0]
    return modname


def remove_prefix(text, prefix):
    """Remove prefix from text."""
    if text.startswith(prefix):
        return text[len(prefix):]

    return text


def format_rst_section(heading: str, level: int = 1):
    """Format reStructuredText section header."""
    underline = ('=-~"' + "'^#*$`")[level - 1]
    return f'{heading}\n{len(heading) * underline}\n\n'


def format_rst_doclet(doc: dict) -> str:
    """Format doclet to JS-sphinx directives."""
    name = doc['name']
    if doc['kind'] == 'function':
        # Use first module name as well to distinguish objects with the same
        # name
        name = doc['longname'].split('/')[-1]
        return f'.. js:autofunction:: {name}\n\n'

    if doc['kind'] == 'class':
        return f'.. js:autoclass:: {name}\n   :members:\n\n'

    if doc['kind'] == 'constant':
        return f'.. js:autoattribute:: {name}\n\n'

    print(f'Do not know what to do with {doc}. Skipping')
    return ''


def format_rst_toctree(entries, maxdepth=4):
    """Format reStructuredText toc tree.

    Example:
        >>> print(format_rst_section('Hello world'))
        Hello world
        ===========
    """
    return f'.. toctree::\n   :maxdepth: {maxdepth}\n\n%s\n\n' % '\n'.join(
        '   ' + e for e in entries
    )


def parse_comment(comment):
    starless = re.sub('\n\s*?\*\s*?', '\n', comment[3:-2]).strip()
    atless = re.sub(r'(?m)^\s*@.*\n?', '', starless)
    return atless


def assign_doclets_to_packages(doclets):
    root = Rst('')

    def resolve_module(modname):
        node = root
        for name in modname.split('/'):
            if name not in node.children:
                Rst(name, parent=node)

            node = node.children[name]

        return node

    for doc in doclets:
        modname = module_name(doc['longname'])
        module = resolve_module(modname)
        if doc['kind'] in ['constant', 'function', 'class']:
            module.doclets.append(doc)
        elif doc['kind'] == 'module':
            module.comment = doc['comment']
        #elif doc['kind'] == 'package':
        #    print(modname, doc['comment'])

    return [
        node
        for node in root.dfs()
        if node.is_package
    ]


def write_package(directory, package):
    fp = os.path.join(directory, package.fullname.replace('/', '.') + '.rst')
    if not package.fullname:
        print(f'Skipping empty file name {fp!r}')
        return

    print(f'Writing to {fp!r}')
    with open(fp, 'w') as f:
        f.write(package.render())


class Node:
    def __init__(self, name, parent=None):
        self.name = name
        self.children = {}
        self.parent = None

        if parent:
            parent.add_child(self)

    @property
    def is_leave(self):
        return len(self.children) == 0

    def add_child(self, child):
        if child.name in self.children:
            raise RuntimeError

        self.children[child.name] = child
        child.parent = self

    def dfs(self):
        queue = collections.deque([self])
        seen = set()
        while queue:
            node = queue.popleft()
            if node in seen:
                continue

            yield node

            seen.add(node)
            queue.extendleft(node.children.values())

    def upstream(self):
        node = self
        while node:
            yield node
            node = node.parent


class Rst(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.doclets = []
        self.comment = ''

    @property
    def is_package(self):
        return not self.is_leave

    @property
    def fullname(self):
        names = [n.name for n in self.upstream()]
        fullname = '/'.join(reversed(names))
        return remove_prefix(fullname, '/')

    def comment_lines(self):
        lines = []
        if self.comment:
            parsed = parse_comment(self.comment)

            # parse_comment() does a good job removing the stars but also leaves
            # the first white space character for all but the first line, which
            # messes up the RST layouting.
            for nr, l in enumerate(parsed.splitlines()):
                if nr > 0 and l:
                    l = l[1:]

                lines.append(l)

            lines.append('')

        return lines

    def render_module(self):
        lines = [format_rst_section(self.fullname, level=2)]
        lines.extend(self.comment_lines())

        for doc in self.doclets:
            lines.append(format_rst_doclet(doc))

        return lines

    def render_package(self):
        subpackages = []
        submodules = []
        for name, child in sorted(self.children.items()):
            if child.is_package:
                subpackages.append(child)
            else:
                submodules.append(child)

        lines = [format_rst_section(self.fullname, level=1)]
        lines.extend(self.comment_lines())
        if subpackages:
            lines.append(format_rst_section('Submodules', level=2))
            entries = [
                pkg.fullname.replace('/', '.')
                for pkg in subpackages
            ]
            lines.append(format_rst_toctree(entries))

        if submodules:
            lines.append(format_rst_section('Submodules', level=2))
            for mod in submodules:
                lines.append(mod.render())

        return lines

    def render(self):
        if self.is_package:
            lines = self.render_package()
        else:
            lines = self.render_module()

        return '\n'.join(lines)



def cli():
    parser = argparse.ArgumentParser(description='JS Apidoc')
    parser.add_argument('sourcedirs', nargs='+', help='path to module to document')
    parser.add_argument('-o', '--output-dir', action='store', dest='destdir', required=True, help='directory to place all output')
    #parser.add_argument('-f', '--force', action='store_true', dest='force', help='overwrite existing files')
    #parser.add_argument('-f', '--force', help='overwrite existing files', action='store_true')
    return parser.parse_args()


def main():
    args = cli()
    sourcedirs = list(map(os.path.abspath, args.sourcedirs))
    os.makedirs(args.destdir, exist_ok=True)
    allDoclets = analyze_js(*sourcedirs)
    doclets = list(filter_doclets(allDoclets))
    packages = assign_doclets_to_packages(doclets)
    for package in packages:
        write_package(args.destdir, package)


if __name__ == '__main__':
    main()
