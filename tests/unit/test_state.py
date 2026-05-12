import src.state as state


def test_state_init_sets_peer_id():
    state.reset()
    state.init_state(0, 0)
    assert state.PEER_ID_STUB


def test_local_catalog_built():
    """Check that local_catalog is a list of entries with required keys."""
    state.reset()
    state.init_state(0, 0)
    catalog = state.local_catalog
    assert isinstance(catalog, list), "local_catalog should be a list"

    for entry in catalog:
        # Check required keys
        assert "file_id" in entry
        assert "name" in entry
        assert "size" in entry
        # Optional: check types
        assert isinstance(entry["file_id"], str)
        assert isinstance(entry["name"], str)
        assert isinstance(entry["size"], int)


if __name__ == "__main__":
    print("Running tests...\n")

    test_state_init_sets_peer_id()
    print("test_state_init_sets_peer_id passed")

    test_local_catalog_built()
    print("test_local_catalog_built passed")
