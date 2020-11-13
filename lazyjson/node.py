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
    ('0123456789.', NodeType.NUMBER),
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
        pass
