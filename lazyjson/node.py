from __future__ import annotations
from enum import Enum, auto
import re

from typing import Dict, List, TextIO, Union

NUMBER_REGEX = re.compile(
    r'''
        ^                       # The beginning of the string
        -?                      # Optional negative sign
        (?: 0 | [1-9]\d* )      # The integral part, which cannot be empty and
                                # cannot start with 0, unless it is exactly 0
        (?: \.\d+ )?            # The optional fractional part
        (?: [eE] [+-]? \d+ )?   # The optional exponent

        # We don't test the end of the string because we need to know where a
        # valid number ends
    ''',
    re.VERBOSE
)


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
    ('0123456789-', NodeType.NUMBER),
]

WHITESPACE = '\r\n\t '

# The maximum number of characters we need to read in order to determine this
# node's type
MAX_NEEDED_CHARS = 5


class Node:
    children_nodes: Union[List[Node], Dict[str, Node]]

    def __init__(self, file: TextIO, pos: int):
        self.file = file

        if not file.seekable():
            raise ValueError('Nodes need to be able to seek into the files')

        # TODO: Ensure the file is opened in binary mode!

        self.skip_to_start(pos)

        self.type = self.get_type()

        if self.type == NodeType.ARRAY:
            self.children_nodes = []
        elif self.type == NodeType.OBJECT:
            self.children_nodes = {}

    def skip_to_start(self, pos):
        self.file.seek(pos)

        self.skip_skippable()

        self.pos = self.file.tell()

    def skip_skippable(self):
        in_comment = False

        while True:
            c = self.file.read(1)

            if c == '':
                raise ValueError('Unexpected end of file')

            if in_comment:
                if c == '\n':
                    in_comment = False
                continue

            if c in WHITESPACE:
                continue

            if c == '/' and self.file.read(1) == '/':
                in_comment = True

                continue

            break

        self.file.seek(self.file.tell() - 1)

    def skip_comma(self):
        self.skip_skippable()

        if self.file.read(1) == ',':
            self.skip_skippable()

            return True
        else:
            return False

    def peek(self, n):
        self.file.seek(self.pos)

        return self.file.read(n)

    def get_type(self):
        buf = self.peek(MAX_NEEDED_CHARS)

        if not buf:
            raise ValueError('Unexpected end of file')

        for prefix, node_type in SIMPLE_DETERMINANTS:
            if buf.startswith(prefix):
                return node_type

        for options, node_type in COMPLEX_DETERMINANTS:
            if any(buf.startswith(c) for c in options):
                return node_type

        raise ValueError(f'Unexpected input: {buf[0]}')

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
            return self.parse_string()
        elif self.type == NodeType.NUMBER:
            return self.parse_number()

    def compute_value_length(self):
        if self.type == NodeType.TRUE:
            return 4
        elif self.type == NodeType.FALSE:
            return 5
        elif self.type == NodeType.NULL:
            return 4
        elif self.type == NodeType.STRING:
            return measure_string(self.file, self.pos)
        elif self.type == NodeType.NUMBER:
            return measure_number(self.file, self.pos)
        # elif self.type == NodeType.ARRAY:
        #     return ...

    def __getitem__(self, key):
        if self.type not in [NodeType.OBJECT, NodeType.ARRAY]:
            raise ValueError(f'Cannot index values of type {self.type}')

        if self.type == NodeType.ARRAY:
            if not isinstance(key, int):
                raise ValueError(f'Can only index arrays with integers, not {type(key)}')

            if key < 0:
                # TODO: This limitation could be removed if we first parse all children and
                # then interpret the negative index the normal python way
                raise ValueError('Can only retrieve items with a positive index')

            cs = self.children_nodes

            if key < len(cs):
                return cs[key]

            if not cs:
                self.file.seek(self.pos + 1)
            else:
                self.file.seek(cs[-1].pos + cs[-1].compute_value_length())

                if not self.skip_comma():
                    raise ValueError(f'Array only has {len(cs)} children')

            while True:
                child = Node(self.file, self.file.tell())

                cs.append(child)

                if len(cs) == key + 1:
                    return child

                self.file.seek(child.pos + child.compute_value_length())

                if not self.skip_comma():
                    raise ValueError(f'Array only has {len(cs)} children')

        elif self.type == NodeType.OBJECT:
            if not isinstance(key, str):
                raise ValueError(f'Can only index objects with strings, not {type(key)}')

    def parse_string(self):
        string = self.peek(self.compute_value_length())

        parts = []

        prev = 1
        while True:
            backslash = string.find('\\', prev)

            if backslash == -1:
                parts.append(string[prev:-1])
                break

            parts.append(string[prev:backslash])

            next_char = string[backslash + 1]

            MAP = {
                '"' : '"',
                '\\': '\\',
                '/': '/',
                'b': '\b',
                'f': '\f',
                'n': '\n',
                'r': '\r',
                't': '\t',
            }

            escaped = MAP.get(next_char, None)

            if escaped is not None:
                parts.append(escaped)
            elif next_char == 'u':
                codepoint = int(string[backslash + 2:backslash + 6], 16)
                parts.append(chr(codepoint))
            else:
                raise ValueError(f'Unknown escaped sequence: \\{next_char}')

        return ''.join(parts)


    def parse_number(self):
        string = self.peek(self.compute_value_length())

        return float(string)


def measure_string(file: TextIO, pos: int):
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

    # Skip the start quote
    file.seek(pos + 1)
    result = 1

    while True:
        buf = file.read(1024)

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

            result += len(buf)
            continue

        break

    if '\n' in buf[:quote_pos]:
        raise ValueError('End of line while scanning string')

    # We must include the quote in the length of the string
    result += quote_pos + 1

    return result


def measure_number(file: TextIO, pos: int):
    # Grab all valid number characters and parse the result

    file.seek(pos)

    accumulated = []

    while True:
        # TODO: I must ensure that the file is actually buffered, or else this
        # line, reading one character at a time, will take an unnecessary long
        # time to run
        c = file.read(1)

        if c == '':
            break
        elif c in '-+0123456789eE.':
            accumulated.append(c)
        else:
            break

    accumulated = ''.join(accumulated)

    m = NUMBER_REGEX.match(accumulated)

    if m is None:
        raise ValueError(
            f'Number starts with a wrong character {accumulated[0]}'
        )

    return m.end()
