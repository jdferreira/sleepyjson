import io

import pytest
from lazyjson import Node, Reader

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


def test_reader():
    Reader(io.StringIO(TEST_CONTENT))


@pytest.fixture
def sample():
    return Reader(io.StringIO(TEST_CONTENT))


# def test_fails_on_non_existing_keys(sample):
#     with pytest.raises(KeyError):
#         sample['x']
