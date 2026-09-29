"""
Test suite for workspace path sandboxing and traversal protection.
"""

from pathlib import Path
import pytest
from ai_agent.tools.filesystem import resolve_sandbox_path


def test_sandbox_allows_relative_path(tmp_path: Path):
    target = resolve_sandbox_path("test.txt", tmp_path)
    assert target == (tmp_path / "test.txt").resolve()
    assert target.is_relative_to(tmp_path)


def test_sandbox_allows_nested_relative_path(tmp_path: Path):
    target = resolve_sandbox_path("sub/dir/nested.py", tmp_path)
    assert target == (tmp_path / "sub" / "dir" / "nested.py").resolve()
    assert target.is_relative_to(tmp_path)


def test_sandbox_blocks_parent_traversal(tmp_path: Path):
    with pytest.raises(PermissionError) as exc_info:
        resolve_sandbox_path("../outside.txt", tmp_path)
    assert "resolves outside the workspace sandbox" in str(exc_info.value)


def test_sandbox_blocks_deep_parent_traversal(tmp_path: Path):
    with pytest.raises(PermissionError) as exc_info:
        resolve_sandbox_path("sub/../../outside.txt", tmp_path)
    assert "resolves outside the workspace sandbox" in str(exc_info.value)


def test_sandbox_blocks_absolute_outside_path(tmp_path: Path):
    outside_root = tmp_path.parent / "completely_outside.txt"
    with pytest.raises(PermissionError) as exc_info:
        resolve_sandbox_path(str(outside_root), tmp_path)
    assert "resolves outside the workspace sandbox" in str(exc_info.value)
