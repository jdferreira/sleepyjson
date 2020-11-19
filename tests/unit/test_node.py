import io

import pytest
from lazyjson.node import Node, NodeType, measure_string, measure_number


def test_nodes_are_creates_from_file_like_objects():
    Node(io.StringIO('[]'), 0)


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
    assert create_node('0').end_position() == 1
    assert create_node('"a"').end_position() == 3
    assert create_node('null').end_position() == 4
    assert create_node('true').end_position() == 4
    assert create_node('false').end_position() == 5
    assert create_node('[]').end_position() == 2
    assert create_node('[1]').end_position() == 3
    assert create_node('{"a": 0}').end_position() == 8


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


def test_array_nodes_can_consume_their_content():
    assert create_node('[]').value() == []
    assert create_node('[1]').value() == [1]
    assert create_node('["a"]').value() == ['a']
    assert create_node('[[]]').value() == [[]]


def test_object_nodes_can_be_indexed():
    node = create_node('{"a": 0, "b": 1}')

    assert isinstance(node['a'], Node)
    assert node['a'].is_number()
    assert node['a'].value() == 0
    assert node['b'].value() == 1

    with pytest.raises(KeyError):
        node['c']

    with pytest.raises(ValueError):
        create_node('[]')['a']

    with pytest.raises(ValueError):
        create_node('{"a"}')['a']

    with pytest.raises(ValueError):
        create_node('{"a",}')['a']

    with pytest.raises(ValueError):
        create_node('{"a":}')['a']

    with pytest.raises(ValueError):
        create_node('{:}')['a']


def test_object_nodes_have_a_length():
    assert len(create_node('{}')) == 0
    assert len(create_node('{"a": 1}')) == 1
    assert len(create_node('{"a": 1, "b": 2}')) == 2
    assert len(create_node('{"a": 1, "b": 2, "c": "abc"}')) == 3


def test_objects_can_have_trailing_comma():
    assert len(create_node('{"a": 1}')) == 1
    assert len(create_node('{"a": 1,}')) == 1
    assert len(create_node('{"a": 1, }')) == 1
    assert len(create_node('{ "a": 1 , }')) == 1


def test_comments_are_allowed():
    node = create_node('// Comment\n[1, 2, 3, // Another\n]')

    assert node.type == NodeType.ARRAY
    assert len(node) == 3
    assert node[0].value() == 1
    assert node[1].value() == 2
    assert node[2].value() == 3

    with pytest.raises(IndexError):
        node[3]


def test_object_nodes_can_consume_their_content():
    assert create_node('{}').value() == {}
    assert create_node('{"a": 1}').value() == {'a': 1}
    assert create_node('{"a": "b"}').value() == {'a': 'b'}
    assert create_node('{"empty": {}}').value() == {'empty': {}}


def test_deep_node():
    node = create_node('''
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


def test_objects_iterate_over_their_keys():
    node = create_node('{"a": 0, "b": 0, "c": 0}')

    assert sorted(node) == ['a', 'b', 'c']


def test_objects_can_test_key_membership():
    node = create_node('{"a": 0}')

    assert 'a' in node
    assert 'b' not in node

def test_arrays_can_test_membership():
    node = create_node('["red", "green", "blue"]')

    assert "red" in node
    assert "black" not in node


def test_object_membership_stops_scanning_when_key_is_found():
    node = create_node('{"a": 0 this is invalid JSON')

    with pytest.raises(ValueError):
        node.value()

    assert 'a' in node

    with pytest.raises(ValueError):
        assert 'b' in node


def test_malformed_json_is_not_read_unless_requested():
    node = create_node('{"a": [], invalid json follows!!!')

    assert node.type == NodeType.OBJECT
    assert node['a'].is_array()
    assert len(node['a']) == 0

    with pytest.raises(ValueError):
        node['b']


def test_array_nodes_can_be_iterated():
    assert [i.value() for i in create_node('[0, false]')] == [0, False]

def test_object_nodes_can_be_iterated():
    assert sorted(create_node('{"a": 0, "b": false}')) == ['a', 'b']

def test_iterating_over_malformed_json_is_allowed_before_the_invalid_region_is_reached():
    it = iter(create_node('[0, false, invalid json'))

    assert next(it).value() == 0
    assert next(it).value() == False

    it = iter(create_node('[0, false // unterminated json'))

    assert next(it).value() == 0
    assert next(it).value() == False

    it = iter(create_node('{"a": 0, "b": false, invalid json'))

    assert next(it) == 'a'
    assert next(it) == 'b'

    it = iter(create_node('{"a": 0, "b": false // unterminated json'))

    assert next(it) == 'a'
    assert next(it) == 'b'


def test_items_not_followed_by_comma_are_the_end_of_the_container():
    with pytest.raises(ValueError):
        create_node('[0, false null]').value()


def test_strings_escape_their_contents():
    create_node('"\\r\\n"').value() == '\r\n'


def test_iterating_over_nodes_works_even_if_file_cursors_changes():
    node = create_node('[0, false]')

    first_child = node[0]
    expected = [0, False]

    for child, expected_item in zip(node, expected):
        assert first_child.value() == 0
        assert child.value() == expected_item


def test_number_nodes_return_int_or_float():
    values = [
        ('-10', int),
        ('0', int),
        ('1', int),
        ('3.14', float),
        ('1.337e3', float),
        ('1e3', float),
    ]

    for string, expected_type in values:
        assert type(create_node(string).value()) == expected_type


def test_nodes_implement_equality():
    assert create_node('["red", "green"]').equals(['red', 'green'])
    assert create_node('{"red": "green"}').equals({'red': 'green'})
    assert create_node('"rgb"').equals('rgb')


def test_nodes_implement_lazy_equality():
    assert not create_node('["red", "green" invalid').equals(['red', 'black'])
    assert not create_node('{"red": "green" invalid').equals({'red': 'black'})
