from __future__ import annotations
from enum import Enum, auto

from typing import TextIO


class NodeType(Enum):
    OBJECT = auto()
    ARRAY = auto()
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()


SIMPLE_DETERMINANTS = [
    ('{', NodeType.OBJECT),
    ('[', NodeType.ARRAY),
    ('"', NodeType.STRING),
    ('true', NodeType.TRUE),
    ('false', NodeType.FALSE),
    ('null', NodeType.NULL),
]

COMPLEX_DETERMINANTS = [
    ('0123456789.-', NodeType.NUMBER),
]

WHITESPACE = '\r\n\t '

# The maximum number of characters we need to read in order to determine this
# node's type
MAX_NEEDED_CHARS = 5


class Node:
    def __init__(self, file: TextIO, pos: int):
        self.file = file
        self.pos = pos

        if not file.seekable():
            raise ValueError('Nodes need to be able to seek into the files')

        # TODO: Ensure the file is opened in binary mode!

        self.type = self.get_type()

    def peek(self, n):
        result = self.file.read(n)

        self.file.seek(self.pos)

        return result

    def get_type(self):
        # Consume whitespace
        while True:
            if self.peek(1) == '':
                raise ValueError('Nodes cannot be empty')
            else:
                break

        buf = self.peek(MAX_NEEDED_CHARS)

        for prefix, node_type in SIMPLE_DETERMINANTS:
            if buf.startswith(prefix):
                return node_type

        for options, node_type in COMPLEX_DETERMINANTS:
            if any(buf.startswith(c) for c in options):
                return node_type

        raise ValueError('Node received unexpected input')

    def is_object(self):
        return self.type == NodeType.OBJECT

    def is_array(self):
        return self.type == NodeType.ARRAY

    def is_string(self):
        return self.type == NodeType.STRING

    def is_number(self):
        return self.type == NodeType.NUMBER

    def is_true(self):
        return self.type == NodeType.TRUE

    def is_false(self):
        return self.type == NodeType.FALSE

    def is_boolean(self):
        return self.is_true() or self.is_false()

    def is_null(self):
        return self.type == NodeType.NULL

    def is_array(self):
        return self.type == NodeType.ARRAY

    def value(self):
        if self.type == NodeType.TRUE:
            return True
        elif self.type == NodeType.FALSE:
            return False
        elif self.type == NodeType.NULL:
            return None
        elif self.type == NodeType.STRING:
            return parse_string(self.file, self.pos)
        elif self.type == NodeType.NUMBER:
            return parse_number(self.file, self.pos)


def parse_string(file: TextIO, pos: int):
    # Repeat this:
    # - Read a bunch characters
    # - If 0 characters were returned, the string did not end... Raise
    #   exception
    # - Repeat this:
    #   - Look for the first occurrence of a "\n" or a quote
    #   - If we found a "\n", the string is not properly finished. Raise
    #     exception
    #   - If it is a non-escaped quote, we found the end of the string!
    #     Return

    file.seek(pos + 1)  # Skip the start quote

    accumulated = []

    while True:
        buf = file.read(1024)  # This buffers starts as with the quote

        if len(buf) == 0:
            raise ValueError('The string does not terminate')

        quote_pos = 0
        while True:
            quote_pos = buf.find('"', quote_pos)

            if quote_pos == -1:
                break
            elif buf[quote_pos - 1] == '\\':
                # Skip this quote
                quote_pos += 1

                continue
            else:
                break

        if quote_pos == -1:
            # We did not find a quote, so we need to search longer
            if '\n' in buf:
                raise ValueError('End of line while scanning string')

            accumulated.append(buf)
            continue

        break

    if '\n' in buf[:quote_pos]:
        raise ValueError('End of line while scanning string')

    # We now have a string
    accumulated.append(buf[:quote_pos])

    return eval('"' + ''.join(accumulated) + '"')


def parse_number(file: TextIO, pos: int):
    # Grab all valid number characters and parse the result

    accumulated = []

    while True:
        c = file.read(1)

        if c == '':
            break
        elif c in '-+0123456789eE.':
            accumulated.append(c)
        else:
            break

    accumulated = ''.join(accumulated)

    return float(accumulated)
