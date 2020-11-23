import gc
import psutil
import pytest

from sleepyjson import Reader
from json_generator import generate_big_json

FILENAME = 'tmp.json'


def get_memory_usage():
    gc.collect()

    return psutil.Process().memory_info().rss


@pytest.mark.slow
def test_long_sample():
    generate_big_json(FILENAME)

    # This test is a bit brittle. The idea is to test that the memory usage when
    # reading the whole object into an actual python dictionary is much higher
    # than the memory usage when just iterating over the file. I'm not even sure
    # what I'm doing here...

    with open(FILENAME) as f:
        start_memory = get_memory_usage()
        reader = Reader(f)
        value = reader.value()
        memory_usage_with_full_value = get_memory_usage() - start_memory

    del value

    with open(FILENAME) as f:
        start_memory = get_memory_usage()
        reader = Reader(f)
        length = len(reader)
        memory_usage_on_iteration_only = get_memory_usage() - start_memory

    del length

    assert memory_usage_on_iteration_only < memory_usage_with_full_value / 1000


if __name__ == '__main__':
    generate_big_json(FILENAME)
