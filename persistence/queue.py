"""Write-behind queue for persisting incidents without blocking simulation.
The queue buffers incident dictionaries and flushes them in batches via
IncidentRepo. If the DB is unavailable the buffer is retained and a degraded
flag is set, which can be shown in the UI.
"""

import threading
import logging
from typing import List, Dict

from .repo import IncidentRepo

logger = logging.getLogger(__name__)


class WriteBehindQueue:
    def __init__(self, batch_size: int = 50):
        self._batch_size = batch_size
        self._buffer: List[Dict] = []
        self._lock = threading.Lock()
        self._degraded = False

    def enqueue(self, incident_dict: Dict) -> None:
        with self._lock:
            self._buffer.append(incident_dict)
            if len(self._buffer) >= self._batch_size:
                self.flush()

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            try:
                for inc in self._buffer:
                    IncidentRepo.create_from_dict(inc)
                self._buffer.clear()
                self._degraded = False
            except Exception as e:
                logger.error("Failed to flush incident queue: %s", e)
                self._degraded = True
                # keep buffer for retry

    def is_degraded(self) -> bool:
        return self._degraded
