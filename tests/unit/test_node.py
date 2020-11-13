import io

import pytest
from lazyjson import Node

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
    return io.StringIO(TEST_CONTENT)
