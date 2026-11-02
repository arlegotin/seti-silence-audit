from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def repo_root():
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def tiny_geometry():
    def make(points):
        from seti_audit.contracts import Geometry

        xyz = np.asarray(points, dtype=np.float64)
        return Geometry(tuple(str(i) for i in range(len(xyz))), xyz,
                        np.linalg.norm(xyz, axis=1),
                        np.linalg.norm(xyz[:, None] - xyz[None, :], axis=2))
    return make
