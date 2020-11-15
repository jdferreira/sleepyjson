import io
import os

import lazyjson
import pytest

TEST_CONTENT = '''
    {
        "a": ["this", "is", "an", "array"],
        "b": {"This": "is", "an": "object"},
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
    return lazyjson.Reader(io.StringIO(TEST_CONTENT))


@pytest.fixture
def multi_sample():
    return lazyjson.Reader([
        io.StringIO(TEST_CONTENT),
        io.StringIO(TEST_CONTENT),
        io.StringIO(TEST_CONTENT)
    ])


def test_integration(sample):
    assert sample['a'][0].value() == 'this'
    assert sample['b']['a'].value() == 'map'
    assert sample['c'][2].value() == None
    assert sample['d'].value() == [1, 2, 3]
    assert sample['e'].value() == 'Trailing commas are allowed'

    sample.next()

    assert sample[0] == 'We can also have multiple objects per file'

    sample.next()

    assert sample[0]['a']['b'][1][0]['c'].value() == None
    assert sample.value() == [{'a': {'b': [[], [{'c': None}]]}}]


def test_type(sample):
    assert sample['a'].is_array()

    assert sample['b'].is_object()

    assert sample['c'][0].is_true()
    assert sample['c'][1].is_false()
    assert sample['c'][2].is_null()
    assert sample['c'][0].is_boolean()
    assert sample['c'][1].is_boolean()

    assert sample['d'][0].is_number()

    assert sample['e'].is_string()


def test_can_access_keys(sample):
    assert sample.keys() == ['a', 'b', 'c', 'd', 'e']


def test_can_go_back(sample):
    assert sample['e'].value() == 'Trailing commas are allowed'
    assert sample['a'][0].value() == 'this'

    sample.next()
    sample.next()
    sample.prev()
    assert sample.is_array()

    sample.seek(0)
    assert sample.is_object() and sample.keys() == ['a', 'b', 'c', 'd', 'e']


def test_membership(sample):
    assert 'a' in sample
    assert sample.has_key('a')


def test_length(sample):
    assert len(sample) == 5
    assert len(sample['a']) == 4
    assert len(sample['b']) == 2


def test_end_of_stream(sample):
    sample.next()
    sample.next()
    sample.next()

    assert sample.finished()


def test_multiple_files(multi_sample):
    multi_sample.seek(7)
    multi_sample[0].is_string()


@pytest.fixture
def long_sample():
    if not os.path.exists('tmp.json'):
        with open('tmp.json', 'w') as f:
            for repeat in range(1000):
                print(f'// Object #{repeat}', file=f)
                print('[', file=f)
                for idx in range(repeat):
                    print(f'    "item {idx} in object #{repeat}",', file=f)
                print(']', file=f)

    with open('tmp.json') as f:
        yield lazyjson.Reader(f)


def test_small_memory_footprint(long_sample):
    assert len(long_sample) == 0

    long_sample.seek(500)

    assert len(long_sample) == 500
    assert long_sample[499].is_string()

    # TODO: Test memory footprint here!
