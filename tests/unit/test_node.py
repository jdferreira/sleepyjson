import io

import pytest
from lazyjson.node import Node, measure_string, measure_number


def create_node(content, pos=0):
    return Node(io.StringIO(content), pos)


def test_nodes_need_characters():
    with pytest.raises(ValueError):
        create_node('')

    with pytest.raises(ValueError):
        create_node('[]', 2)


def test_nodes_know_their_type():
    assert create_node('{}').is_object()
    assert create_node('[]').is_array()
    assert create_node('""').is_string()
    assert create_node('12').is_number()
    assert create_node('true').is_true()
    assert create_node('false').is_false()
    assert create_node('true').is_boolean()
    assert create_node('null').is_null()

    with pytest.raises(ValueError):
        assert create_node('undefined')


def test_simple_nodes_can_consume_their_content():
    assert create_node('true').value() == True
    assert create_node('false').value() == False
    assert create_node('null').value() == None
    assert create_node('""').value() == ''
    assert create_node('12').value() == 12


def test_measure_string():
    def measure(text):
        return measure_string(io.StringIO(text), 0)

    assert measure('"abc"') == 5
    assert measure('""') == 2
    assert measure('"\\""') == 4
    assert measure('"He said \\"Watch out\\"!"') == 24

    with pytest.raises(ValueError):
        measure('"')

    with pytest.raises(ValueError):
        measure('"New \n line"')


def test_measure_number():
    def measure(text):
        return measure_number(io.StringIO(text), 0)

    assert measure('3.14') == 4
    assert measure('1000') == 4
    assert measure('-666') == 4
    assert measure('5e-8') == 4
    assert measure('0.12') == 4
    assert measure('1.1e1') == 5

    # Numbers followed by other stuff
    assert measure('1+2') == 1
    assert measure('1e-5e') == 4
    assert measure('0123') == 1

    with pytest.raises(ValueError):
        measure('.3.8')

    with pytest.raises(ValueError):
        measure('.123')


def test_nodes_know_where_they_end():
    test_content = '{"a": [1, true, false, null]}'

    test_cases = [
        # (0, '{"a": [1, true, false, null]}'),
        (1, '"a"'),
        (6, '[1, true, false, null]'),
        (7, '1'),
        (10, 'true'),
        (16, 'false'),
        (23, 'null'),
    ]

    for i, value_repr in test_cases:
        node = create_node(test_content, i)

        assert node.compute_value_length() == len(value_repr)


def test_array_nodes_can_be_indexed():
    node = create_node('[1, 23, 456]')

    assert isinstance(node[0], Node)
    assert node[0].is_number()
    assert node[0].value() == 1
    assert node[1].value() == 23
    assert node[2].value() == 456

    assert node[-1].value() == 456
    assert node[-2].value() == 23
    assert node[-3].value() == 1

    with pytest.raises(ValueError):
        create_node('{}')[0]

    with pytest.raises(IndexError):
        create_node('[]')[0]

    with pytest.raises(IndexError):
        create_node('[]')[-1]


def test_array_nodes_have_a_length():
    assert len(create_node('[]')) == 0
    assert len(create_node('[1]')) == 1
    assert len(create_node('[1, 2]')) == 2
    assert len(create_node('[1, 2, "abc"]')) == 3


def test_arrays_can_have_trailing_comma():
    assert len(create_node('[1]')) == 1
    assert len(create_node('[1,]')) == 1
    assert len(create_node('[1, ]')) == 1
    assert len(create_node('[ 1 , ]')) == 1


def test_object_nodes_can_be_indexed():
    node = create_node('{"a": 123}')

    assert isinstance(node['a'], Node)
    assert node['a'].is_number()
    assert node['a'].value() == 123

    with pytest.raises(ValueError):
        create_node('""')['a']
