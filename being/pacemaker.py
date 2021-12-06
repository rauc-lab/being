"""Pacemaker thread."""
import contextlib
import threading
from typing import Any

from being.backends import CanBackend
from being.configuration import CONFIG
from being.logging import get_logger


INTERVAL = CONFIG['General']['INTERVAL']


class Once:

    """Value changed detector."""

    def __init__(self, initial: Any):
        """
        Args:
            initial: Initial value.
        """
        self.prev = initial

    def changed(self, value: Any) -> bool:
        """Check if value changed since last call.

        Args:
            value: Value to check.

        Returns:
            True if value changed since last call. False otherwise.
        """
        if value == self.prev:
            return False

        self.prev = value
        return True


class Pacemaker(contextlib.AbstractContextManager):

    """Pacemaker / watchdog / dead man's switch daemon thread.

    Can step in to trigger SYNC messages and  PDO transmission if main thread is
    not on time. In order to prevent RPDO timeouts.

    Note:
        Does not start by default (:meth:`Pacemaker.start`). Can be used as
        dummy if unstarted.
    """

    def __init__(self, network: CanBackend, maxWait: float = 1.2 * INTERVAL):
        """
        Args:
            network: CanBackend network instance to trigger PDO transmits / SYNC
                messages.
            maxWait: Maximum wait duration before stepping in. Some portion
                larger than global :attr:`INTERVAL`.
        """
        self.network = network
        self.maxWait = maxWait
        self.logger = get_logger('Pacemaker')
        self.pulseEvent = threading.Event()
        self.running = False
        self.thread = None
        self.once = Once(initial=True)

    def tick(self):
        """Push the dead man's switch."""
        self.pulseEvent.set()

    def _run(self):
        while self.running:
            if self.pulseEvent.wait(timeout=self.maxWait):
                if self.once.changed(True):
                    self.logger.warning('Off')

            else:
                self.network.transmit_all_rpdos()
                self.network.send_sync()
                if self.once.changed(False):
                    self.logger.warning('On')

            self.pulseEvent.clear()

    def start(self):
        """Start watchdog daemon thread."""
        if self.running:
            raise RuntimeError('Watchdog thread already running!')

        self.logger.info('Starting watchdog thread')
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop watchdog daemon thread."""
        if not self.running:
            raise RuntimeError('No watchdog thread running!')

        self.logger.info('Stopping watchdog thread')
        self.running = False
        self.tick()
        self.thread.join()

    def __enter__(self):
        #self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
