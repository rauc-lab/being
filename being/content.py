"""Content manager. Manages spline motions in content directory. Motion model."""
import os
import glob
import json
import logging

from being.serialization import loads, dumps
from being.utils import rootname, SingleInstanceCache


class Content(SingleInstanceCache):

    """Content manager. For now only motions / splines."""

    # TODO: Hoist IO!
    # TODO: Inversion of control (IoC)
    # TODO: Extend for all kind of files, subfolders.

    def __init__(self, directory='content'):
        self.directory = directory
        self.logger = logging.getLogger(str(self))
        os.makedirs(self.directory, exist_ok=True)

    def _fullpath(self, name):
        """Resolve full path for given name."""
        return os.path.join(self.directory, name + '.json')

    def motion_exists(self, name):
        fp = self._fullpath(name)
        return os.path.exists(fp)

    def load_motion(self, name):
        self.logger.debug('Loading motion %r', name)
        fp = self._fullpath(name)
        with open(fp) as f:
            return loads(f.read())

    def save_motion(self, spline, name):
        self.logger.debug('Saving motion %r', name)
        fp = self._fullpath(name)
        with open(fp, 'w') as f:
            f.write(dumps(spline))

    def delete_motion(self, name):
        self.logger.debug('Deleting motion %r', name)
        fp = self._fullpath(name)
        os.remove(fp)

    def list_motions(self):
        return [rootname(fp) for fp in glob.glob(self.directory + '/*.json')]

    def __str__(self):
        return '%s(directory=%r)' % (type(self).__name__, self.directory)
