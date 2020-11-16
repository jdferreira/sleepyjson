from io import BytesIO

import pytest
from lazyjson import Node, Reader, NodeType

TEST_CONTENT = b'''
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
    return Reader(BytesIO(TEST_CONTENT))


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

    with pytest.raises(ValueError):
        sample.next()

def test_reader_can_go_back(sample):
    sample.next()
    sample.next()
    sample.prev()
    assert sample.is_array()


def test_reader_can_seek_values(sample):
    sample.seek(0)
    assert sample.is_object() and len(sample) == 5

    sample.seek(2)
    assert sample[0]['a'].is_object()

    with pytest.raises(IndexError):
        sample.seek(3)

    with pytest.raises(IndexError):
        sample.seek(-1)
