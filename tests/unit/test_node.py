import io

import pytest
from lazyjson.node import Node, NodeType, measure_string, measure_number


def test_nodes_fail_on_text_io():
    Node(io.BytesIO(b'[]'), 0)

    with pytest.raises(ValueError):
        Node(io.StringIO('[]'), 0)


def create_node(content, pos=0):
    return Node(io.BytesIO(content), pos)


def test_nodes_need_characters():
    with pytest.raises(ValueError):
        create_node(b'')

    with pytest.raises(ValueError):
        create_node(b'[]', 2)


def test_nodes_know_their_type():
    assert create_node(b'{}').is_object()
    assert create_node(b'[]').is_array()
    assert create_node(b'""').is_string()
    assert create_node(b'12').is_number()
    assert create_node(b'true').is_true()
    assert create_node(b'false').is_false()
    assert create_node(b'true').is_boolean()
    assert create_node(b'null').is_null()

    with pytest.raises(ValueError):
        assert create_node(b'undefined')


def test_simple_nodes_can_consume_their_content():
    assert create_node(b'true').value() == True
    assert create_node(b'false').value() == False
    assert create_node(b'null').value() == None
    assert create_node(b'""').value() == ''
    assert create_node(b'12').value() == 12


def test_measure_string():
    def measure(text):
        return measure_string(io.BytesIO(text), 0)

    assert measure(b'"abc"') == 5
    assert measure(b'""') == 2
    assert measure(b'"\\""') == 4
    assert measure(b'"He said \\"Watch out\\"!"') == 24

    with pytest.raises(ValueError):
        measure(b'"')

    with pytest.raises(ValueError):
        measure(b'"New \n line"')


def test_measure_number():
    def measure(text):
        return measure_number(io.BytesIO(text), 0)

    assert measure(b'3.14') == 4
    assert measure(b'1000') == 4
    assert measure(b'-666') == 4
    assert measure(b'5e-8') == 4
    assert measure(b'0.12') == 4
    assert measure(b'1.1e1') == 5

    # Numbers followed by other stuff
    assert measure(b'1+2') == 1
    assert measure(b'1e-5e') == 4
    assert measure(b'0123') == 1

    with pytest.raises(ValueError):
        measure(b'.3.8')

    with pytest.raises(ValueError):
        measure(b'.123')


def test_nodes_know_where_they_end():
    test_content = b'{"a": [1, true, false, null]}'

    test_cases = [
        (0, b'{"a": [1, true, false, null]}'),
        (1, b'"a"'),
        (6, b'[1, true, false, null]'),
        (7, b'1'),
        (10, b'true'),
        (16, b'false'),
        (23, b'null'),
    ]

    for i, value_repr in test_cases:
        node = create_node(test_content, i)

        assert node.compute_value_length() == len(value_repr)


def test_array_nodes_can_be_indexed():
    node = create_node(b'[1, 23, 456]')

    assert isinstance(node[0], Node)
    assert node[0].is_number()
    assert node[0].value() == 1
    assert node[1].value() == 23
    assert node[2].value() == 456

    assert node[-1].value() == 456
    assert node[-2].value() == 23
    assert node[-3].value() == 1

    with pytest.raises(ValueError):
        create_node(b'{}')[0]

    with pytest.raises(IndexError):
        create_node(b'[]')[0]

    with pytest.raises(IndexError):
        create_node(b'[]')[-1]


def test_array_nodes_have_a_length():
    assert len(create_node(b'[]')) == 0
    assert len(create_node(b'[1]')) == 1
    assert len(create_node(b'[1, 2]')) == 2
    assert len(create_node(b'[1, 2, "abc"]')) == 3


def test_arrays_can_have_trailing_comma():
    assert len(create_node(b'[1]')) == 1
    assert len(create_node(b'[1,]')) == 1
    assert len(create_node(b'[1, ]')) == 1
    assert len(create_node(b'[ 1 , ]')) == 1


def test_array_nodes_can_consume_their_content():
    assert create_node(b'[]').value() == []
    assert create_node(b'[1]').value() == [1]
    assert create_node(b'["a"]').value() == ['a']
    assert create_node(b'[[]]').value() == [[]]


def test_object_nodes_can_be_indexed():
    node = create_node(b'{"a": 0, "b": 1}')

    assert isinstance(node['a'], Node)
    assert node['a'].is_number()
    assert node['a'].value() == 0
    assert node['b'].value() == 1

    with pytest.raises(KeyError):
        node['c']

    with pytest.raises(ValueError):
        create_node(b'[]')['a']

    with pytest.raises(ValueError):
        create_node(b'{"a"}')['a']

    with pytest.raises(ValueError):
        create_node(b'{"a",}')['a']

    with pytest.raises(ValueError):
        create_node(b'{"a":}')['a']

    with pytest.raises(ValueError):
        create_node(b'{:}')['a']


def test_object_nodes_have_a_length():
    assert len(create_node(b'{}')) == 0
    assert len(create_node(b'{"a": 1}')) == 1
    assert len(create_node(b'{"a": 1, "b": 2}')) == 2
    assert len(create_node(b'{"a": 1, "b": 2, "c": "abc"}')) == 3


def test_objects_can_have_trailing_comma():
    assert len(create_node(b'{"a": 1}')) == 1
    assert len(create_node(b'{"a": 1,}')) == 1
    assert len(create_node(b'{"a": 1, }')) == 1
    assert len(create_node(b'{ "a": 1 , }')) == 1


def test_comments_are_allowed():
    node = create_node(b'// Comment\n[1, 2, 3, // Another\n]')

    assert node.type == NodeType.ARRAY
    assert len(node) == 3
    assert node[0].value() == 1
    assert node[1].value() == 2
    assert node[2].value() == 3

    with pytest.raises(IndexError):
        node[3]


def test_object_nodes_can_consume_their_content():
    assert create_node(b'{}').value() == {}
    assert create_node(b'{"a": 1}').value() == {'a': 1}
    assert create_node(b'{"a": "b"}').value() == {'a': 'b'}
    assert create_node(b'{"empty": {}}').value() == {'empty': {}}


def test_deep_node():
    node = create_node(b'''
        {
            // Comment
            "a": [1, 2, 3, ["inner", "string"]],
            "b": "String",
            "c": {"d": {"e": [false, false]}},
        }
    ''')

    assert node['a'][0].value() == 1
    assert node['a'][3].value() == ['inner', 'string']
    assert node['c']['d']['e'][0].value() == False

    assert node.value() == {
        'a': [1, 2, 3, ['inner', 'string']],
        'b': 'String',
        'c': {'d': {'e': [False, False]}},
    }
