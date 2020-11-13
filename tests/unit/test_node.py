import io

import pytest
from lazyjson import Node


def create_node(content, pos):
    return Node(io.StringIO(content), pos)


def test_nodes_need_files_and_positions():
    create_node('[]', 0)


def test_nodes_know_their_type():
    assert create_node('{}', 0).is_object()
    assert create_node('[]', 0).is_array()
    assert create_node('""', 0).is_string()
    assert create_node('12', 0).is_number()
    assert create_node('true', 0).is_true()
    assert create_node('false', 0).is_false()
    assert create_node('true', 0).is_boolean()
    assert create_node('null', 0).is_null()

    with pytest.raises(ValueError):
        assert create_node('undefined', 0)
