"""SQLAlchemy types for PostgreSQL + asyncpg."""

from __future__ import annotations

import numpy as np
from pgvector.sqlalchemy import VECTOR


class AsyncPgVector(VECTOR):
    """pgvector column type that binds as float32 numpy arrays for asyncpg."""

    cache_ok = True

    def bind_processor(self, dialect):  # noqa: ANN001
        def process(value):  # noqa: ANN001
            if value is None:
                return None
            arr = np.asarray(value, dtype=np.float32)
            if arr.ndim != 1 or arr.shape[0] != self.dim:
                raise ValueError(f"expected vector dim {self.dim}, got shape {arr.shape}")
            return arr

        return process
