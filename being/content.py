"""Content manager. Manages spline motions in content directory. Motion model."""
import os
import glob
import logging
import shutil
from typing import List

from being.serialization import loads, dumps
from being.utils import rootname, read_file, write_file, SingleInstanceCache


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

    def _sorted_names(self):
        """All motion names present. Sorted according to creation / modified
        date.
        """
        filepaths = glob.glob(self.directory + '/*.json')
        return map(rootname, sorted(filepaths, key=os.path.getctime))

    def motion_exists(self, name):
        fp = self._fullpath(name)
        return os.path.exists(fp)

    def load_motion(self, name):
        #self.logger.debug('Loading motion %r', name)
        fp = self._fullpath(name)
        return loads(read_file(fp))

    def save_motion(self, spline, name):
        #self.logger.debug('Saving motion %r', name)
        fp = self._fullpath(name)
        write_file(fp, dumps(spline))

    def rename_motion(self, name, new_name):
        #self.logger.debug('Rename motion %r to %r', name, new_name)
        fp = self._fullpath(name)
        new_fp = self._fullpath(new_name)
        os.rename(fp, new_fp)

    def duplicate_motion(self, name):
        #self.logger.debug('Duplicate motion %r', name)
        fp = self._fullpath(name)
        fp_copy = self._fullpath(name + "_COPY")
        shutil.copyfile(fp, fp_copy)

    def delete_motion(self, name):
        #self.logger.debug('Deleting motion %r', name)
        fp = self._fullpath(name)
        os.remove(fp)

    def list_motions(self) -> list:
        return [
            (name, self.load_motion(name))
            for name in self._sorted_names()
        ]

    def dict_motions(self) -> List[dict]:
        # TODO: Misleading name. Method is not returning a dict
        return [
            {
                'filename': name,
                'content': self.load_motion(name),
            }
            for name in self._sorted_names()
        ]

    def __str__(self):
        return '%s(directory=%r)' % (type(self).__name__, self.directory)
