"""Content manager. Manages spline motions in content directory. Motion model."""
import os
import glob
import shutil
from typing import List, Generator

from being.config import CONFIG
from being.logging import get_logger
from being.pubsub import PubSub
from being.serialization import loads, dumps
from being.spline import BPoly
from being.utils import rootname, read_file, write_file, SingleInstanceCache


CONTENT_CHANGED = 'CONTENT_CHANGED'
"""String literal for PubSub Event."""

NameGenerator = Generator[str, None, None]
"""Motion names generator."""

DEFAULT_DIRECTORY = CONFIG['General']['CONTENT_DIRECTORY']
"""Default content directory."""


class Content(PubSub, SingleInstanceCache):

    """Content manager. For now only motions / splines."""

    # TODO: Hoist IO!
    # TODO: Inversion of control (IoC)
    # TODO: Extend for all kind of files, subfolders.

    def __init__(self, directory: str = DEFAULT_DIRECTORY):
        super().__init__(events=[CONTENT_CHANGED])
        self.directory = directory
        self.logger = get_logger(str(self))
        os.makedirs(self.directory, exist_ok=True)

    def _fullpath(self, name: str) -> str:
        """Resolve full path for given name."""
        return os.path.join(self.directory, name + '.json')

    def _recently_modified_names(self) -> NameGenerator:
        """All motion names in recently modified order."""
        filepaths = glob.glob(self.directory + '/*.json')
        return map(rootname, sorted(filepaths, key=os.path.getctime))

    def _sorted_names(self) -> NameGenerator:
        """All motion names sorted."""
        filepaths = glob.glob(self.directory + '/*.json')
        return map(rootname, sorted(filepaths))

    def find_free_name(self, wishName='Untitled'):
        """Find free name. Append numbers starting from 1 if name is already taken.

        Args:
            wishName: Wish name.

        Returns:
            Available version of wish name.

        Raises:
            RuntimeError: If we can not find any available name (after x tries...)
        """
        names = list(self._sorted_names())
        if wishName not in names:
            return wishName

        for number in range(1, 100):
            name = f'{wishName} {number}'
            if name not in names:
                return name

        raise RuntimeError('Can not find any free name!')

    def motion_exists(self, name: str) -> bool:
        """Check if motion exists.

        Args:
            name: Motion name.

        Returns:
            If motion exists.
        """
        fp = self._fullpath(name)
        return os.path.exists(fp)

    def load_motion(self, name: str) -> BPoly:
        """Load spline from disk.

        Args:
            name: Motion name.

        Returns:
            Spline
        """
        fp = self._fullpath(name)
        return loads(read_file(fp))

    def save_motion(self, name: str, spline: BPoly):
        """Save spline to disk.

        Args:
            spline: Spline to save.
            name: Motion name.
        """
        fp = self._fullpath(name)
        write_file(fp, dumps(spline))
        self.publish(CONTENT_CHANGED)

    def delete_motion(self, name: str):
        """Delete motion from disk.

        Args:
            name: Motion name.
        """
        fp = self._fullpath(name)
        os.remove(fp)
        self.publish(CONTENT_CHANGED)

    def list_motions(self) -> list:
        """Get list representation of all motions."""
        return [
            (name, self.load_motion(name))
            for name in self._recently_modified_names()
        ]

    def dict_motions(self) -> List[dict]:
        """Get list with dict representation of all motions."""
        # TODO: Misleading name. Method is not returning a dict
        return [
            {
                'filename': name,
                'content': self.load_motion(name),
            }
            for name in self._recently_modified_names()
        ]

    def dict_motions_2(self) -> dict:
        """Get dict only representation of all motions."""
        return {
            'type': 'motions',
            'splines': {
                name: self.load_motion(name)
                for name in self._sorted_names()
            }
        }

    def __str__(self):
        return '%s(directory=%r)' % (type(self).__name__, self.directory)
