import io
from io import StringIO

import pytest
from lazyjson.node import Node, NodeType
from lazyjson.reader import Reader

TEST_CONTENT = '''
    {
        "a": ["this", "is", "a", "sequence"],
        "b": {"This": "is", "a": "map"},
        "c": [true, false, null],
        // This is a comment, and is allowed and ignored
        "d": [1, 2, 3],
        "e": "Trailing commas are allowed",
    }
    [
        "We can also have multiple objects per file",
    ]
    [{"a":{"b":[[], [{"c":null}]]}}]
'''


@pytest.fixture
def sample():
    return Reader(io.StringIO(TEST_CONTENT))


def test_reader_reads_nodes(sample):
    assert sample.type == NodeType.OBJECT
    assert isinstance(sample['a'], Node)
    assert len(sample) == 5


def test_reader_handles_multiple_objects_per_file(sample):
    assert sample.type == NodeType.OBJECT

    sample.next()

    assert sample.type == NodeType.ARRAY
    assert sample[0].value() == 'We can also have multiple objects per file'

    sample.next()

    assert sample[0]['a']['b'][1][0]['c'].value() == None

    with pytest.raises(StopIteration):
        sample.next()

def test_reader_can_jump_values(sample):
    assert sample.is_object() and len(sample) == 5

    sample.jump(2)

    assert sample[0]['a'].is_object()

    with pytest.raises(ValueError):
        sample.jump(-1)

    with pytest.raises(StopIteration):
        sample.jump(1)


def test_end_of_stream(sample):
    sample.next()
    sample.next()

    with pytest.raises(StopIteration):
        sample.next()


def test_readers_on_arrays_or_objects_are_iterables(sample):
    it = iter(sample)

    assert next(it) == 'a'
    assert next(it) == 'b'
    assert next(it) == 'c'
    assert next(it) == 'd'
    assert next(it) == 'e'


def test_reader_handles_multiple_files():
    reader = Reader([
        io.StringIO(TEST_CONTENT),
        io.StringIO(TEST_CONTENT),
        io.StringIO(TEST_CONTENT),
    ])

    reader.jump(7)

    assert reader[0].is_string()


def test_reader_handles_tight_streams():
    reader = Reader(StringIO('"1"[2,3,4]{}'))

    assert reader.value() == '1'

    reader.next()

    assert reader.value() == [2, 3, 4]

    reader.next()

    assert reader.value() == {}

    with pytest.raises(StopIteration):
        assert reader.next()
