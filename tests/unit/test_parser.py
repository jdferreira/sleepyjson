import io

import pytest
from sleepyjson.parser import Parser


def test_measure_string():
    def measure(text):
        return Parser(io.StringIO(text)).measure_string(0)

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
        return Parser(io.StringIO(text)).measure_number(0)

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
