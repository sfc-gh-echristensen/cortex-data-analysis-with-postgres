import sys
from pathlib import Path


def pytest_configure():
    # Ensure project package root is on sys.path so tests can import local modules
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
