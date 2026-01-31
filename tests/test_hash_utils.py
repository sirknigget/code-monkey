"""Tests for hash computation utilities."""

import tempfile
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.utilities.hash_utils import compute_file_hash


class TestComputeFileHash:
    """Test suite for compute_file_hash function."""

    def test_computes_sha256_hash(self):
        """Verify SHA-256 hash matches known value for 'hello world\\n'."""
        # SHA-256 of "hello world\n" is:
        expected_hash = (
            "a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"
        )
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("hello world\n")
            temp_path = f.name

        try:
            result = compute_file_hash(temp_path)
            assert result == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_hash_is_deterministic(self):
        """Same file content produces same hash across calls."""
        content = "deterministic content for testing"
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            hash1 = compute_file_hash(temp_path)
            hash2 = compute_file_hash(temp_path)
            assert hash1 == hash2
        finally:
            Path(temp_path).unlink()

    def test_different_content_different_hash(self):
        """Different file contents produce different hashes."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("content A")
            path_a = f.name

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("content B")
            path_b = f.name

        try:
            hash_a = compute_file_hash(path_a)
            hash_b = compute_file_hash(path_b)
            assert hash_a != hash_b
        finally:
            Path(path_a).unlink()
            Path(path_b).unlink()

    def test_empty_file_hash(self):
        """Empty file has a valid SHA-256 hash."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            temp_path = f.name

        try:
            result = compute_file_hash(temp_path)
            # SHA-256 of empty string is the sha256 of nothing
            # e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            assert result == (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            )
            assert len(result) == 64  # SHA-256 hexdigest is 64 chars
        finally:
            Path(temp_path).unlink()

    def test_raises_on_nonexistent_file(self):
        """OSError is raised when file does not exist."""
        nonexistent_path = "/tmp/this_file_does_not_exist_123456789.xyz"
        assert not Path(nonexistent_path).exists()

        with pytest.raises(OSError):
            compute_file_hash(nonexistent_path)

    def test_accepts_string_path(self):
        """Function accepts string path in addition to Path object."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Pass string instead of Path
            result = compute_file_hash(temp_path)
            assert len(result) == 64
            assert all(c in "0123456789abcdef" for c in result)
        finally:
            Path(temp_path).unlink()

    def test_binary_file_hash(self):
        """Hash works correctly for binary file content."""
        # Write bytes that are not valid UTF-8
        binary_content = b"\x00\x01\x02\xff\xfe\xfd"
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(binary_content)
            temp_path = f.name

        try:
            result = compute_file_hash(temp_path)
            assert len(result) == 64
        finally:
            Path(temp_path).unlink()

    def test_large_file_hash(self):
        """Hash works correctly for larger files (tests streaming)."""
        # Create a 1MB file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"x" * (1024 * 1024))
            temp_path = f.name

        try:
            result = compute_file_hash(temp_path)
            assert len(result) == 64
        finally:
            Path(temp_path).unlink()
