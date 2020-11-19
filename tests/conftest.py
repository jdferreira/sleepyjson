import sys
import pytest

sys.path.insert(0, '')

def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'slow: marks tests as slow (deselect with "--runslow")'
    )

def pytest_addoption(parser):
    parser.addoption(
        '--runslow',
        action='store_true',
        help='run slow tests'
    )

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getvalue('runslow'):
        pytest.skip('Use --runslow option to run this test')


