import io

import pytest
from lazyjson.node import Node, parse_string


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


def test_simple_nodes_can_consume_their_content():
    assert create_node('true', 0).value() == True
    assert create_node('false', 0).value() == False
    assert create_node('null', 0).value() == None
    assert create_node('""', 0).value() == ''
    # assert create_node('12', 0).value() == 12


def test_parse_string():
    def parse(text):
        return parse_string(io.StringIO(text), 0)

    assert parse('"abc"') == 'abc'
    assert parse('""') == ''
    assert parse('"\\""') == '"'
    assert parse('"He said \\"Watch out\\"!"') == 'He said "Watch out"!'

    with pytest.raises(ValueError) as exp_info:
        parse('"')
    assert 'does not terminate' in str(exp_info.value)

    with pytest.raises(ValueError) as exp_info:
        parse('"New \n line"')
    assert 'End of line while scanning string' in str(exp_info.value)
