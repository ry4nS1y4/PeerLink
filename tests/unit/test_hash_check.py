import hashlib
import os
import tempfile

from src.connection.hash_check import verify_file_hash


def _write_temp(content: bytes) -> str:
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_correct_hash_returns_true():
    content = b"hello p2p world"
    path = _write_temp(content)
    result = verify_file_hash(path, _sha256(content))
    assert result is True
    os.unlink(path)


def test_correct_file_not_deleted():
    content = b"keep me around"
    path = _write_temp(content)
    verify_file_hash(path, _sha256(content))
    assert os.path.exists(path)
    os.unlink(path)


def test_wrong_hash_returns_false():
    content = b"real content"
    path = _write_temp(content)
    result = verify_file_hash(path, _sha256(b"different content"))
    assert result is False


def test_mismatched_file_is_deleted():
    content = b"corrupt bytes"
    path = _write_temp(content)
    verify_file_hash(path, _sha256(b"something else"))
    assert not os.path.exists(path)


def test_empty_file_correct_hash():
    path = _write_temp(b"")
    result = verify_file_hash(path, _sha256(b""))
    assert result is True
    os.unlink(path)


def test_empty_file_wrong_hash():
    path = _write_temp(b"")
    result = verify_file_hash(path, _sha256(b"nonempty"))
    assert result is False
    assert not os.path.exists(path)


def test_nonexistent_file_returns_false():
    result = verify_file_hash("/tmp/does_not_exist_xyz.bin", "abc123")
    assert result is False


if __name__ == "__main__":
    print("Running tests...\n")

    test_correct_hash_returns_true()
    print("test_correct_hash_returns_true passed")

    test_correct_file_not_deleted()
    print("test_correct_file_not_deleted passed")

    test_wrong_hash_returns_false()
    print("test_wrong_hash_returns_false passed")

    test_mismatched_file_is_deleted()
    print("test_mismatched_file_is_deleted passed")

    test_empty_file_correct_hash()
    print("test_empty_file_correct_hash passed")

    test_empty_file_wrong_hash()
    print("test_empty_file_wrong_hash passed")

    test_nonexistent_file_returns_false()
    print("test_nonexistent_file_returns_false passed")

    print("\nAll tests passed!")
