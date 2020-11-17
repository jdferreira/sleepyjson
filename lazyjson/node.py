from __future__ import annotations
from enum import Enum, auto
import re

from typing import BinaryIO, Dict, List, Union

NUMBER_REGEX = re.compile(
    br'''
        ^                       # The beginning of the string
        -?                      # Optional negative sign
        (?: 0 | [1-9]\d* )      # The integral part, which cannot be empty and
                                # cannot start with 0, unless it is exactly 0
        (?: \.\d+ )?            # The optional fractional part
        (?: [eE] [+-]? \d+ )?   # The optional exponent

        # We don't test the end of the string because we don't need to know what
        # comes after the valid number
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
    (b'{', NodeType.OBJECT),
    (b'[', NodeType.ARRAY),
    (b'"', NodeType.STRING),
    (b'true', NodeType.TRUE),
    (b'false', NodeType.FALSE),
    (b'null', NodeType.NULL),
]

COMPLEX_DETERMINANTS = [
    (b'0123456789-', NodeType.NUMBER),
]

WHITESPACE = b'\r\n\t '

# The maximum number of characters we need to read in order to determine this
# node's type
MAX_NEEDED_CHARS = 5


class Node:
    children: Union[List[Node], Dict[str, Node]]

    def __init__(self, file: BinaryIO, pos: int):
        self.file = file

        if not file.seekable():
            raise ValueError('Nodes need to be able to seek into the file')

        if not self.is_binary():
            raise ValueError('Nodes need the file to be opened in binary mode')

        self.skip_to_start(pos)

        self.type = self.get_type()

        if self.type == NodeType.ARRAY:
            self.children = []
            self.size = None
            self.end = None
        elif self.type == NodeType.OBJECT:
            self.children = {}
            self.last_key = None
            self.size = None
            self.end = None

    def is_binary(self):
        return self.file.read(0) == b''

    def skip_to_start(self, pos):
        self.file.seek(pos)

        self.skip_skippable()

        self.pos = self.file.tell()

    def skip_skippable(self):
        in_comment = False

        while True:
            c = self.file.read(1)

            if c == b'':
                return

            if in_comment:
                if c == b'\r':
                    pos = self.file.tell()
                    next_c = self.file.read(1)

                    if next_c != b'\n':
                        self.file.seek(pos)
                    in_comment = False
                elif c == b'\n':
                    in_comment = False
                continue

            if c in WHITESPACE:
                continue

            if c == b'/':
                pos = self.file.tell()
                next_c = self.file.read(1)

                if next_c != b'/':
                    self.file.seek(pos)
                else:
                    in_comment = True

                continue

            break

        self.file.seek(self.file.tell() - 1)

    def skip_comma(self):
        self.skip_skippable()

        if self.peek(1) == b',':
            self.file.read(1)

            self.skip_skippable()

            return True
        else:
            return False

    def skip_colon(self):
        self.skip_skippable()

        if self.peek(1) == b':':
            self.file.read(1)

            self.skip_skippable()

            return True
        else:
            return False

    def peek(self, n):
        pos = self.file.tell()

        result = self.file.read(n)

        self.file.seek(pos)

        return result

    def get_type(self):
        self.file.seek(self.pos)

        buf = self.peek(MAX_NEEDED_CHARS)

        if not buf:
            raise ValueError('Unexpected end of file')

        for prefix, node_type in SIMPLE_DETERMINANTS:
            if buf.startswith(prefix):
                return node_type

        for options, node_type in COMPLEX_DETERMINANTS:
            if any(buf[0] == c for c in options):
                return node_type

        raise ValueError(f'Unexpected input: {buf[:10]}')

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
        elif self.type == NodeType.ARRAY:
            self.read_array_children_up_to(None)

            return [child.value() for child in self.children]
        elif self.type == NodeType.OBJECT:
            self.read_object_children_up_to(None)

            return {key: child.value() for key, child in self.children.items()}

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
        elif self.type == NodeType.ARRAY:
            self.read_array_children_up_to(None)

            return self.end - self.pos
        elif self.type == NodeType.OBJECT:
            self.read_object_children_up_to(None)

            return self.end - self.pos

    def end_position(self):
        return self.pos + self.compute_value_length()

    def seek_next_child(self, expecting_next):
        if len(self.children) == 0:
            self.file.seek(self.pos + 1)

            self.skip_skippable()

            return False
        else:
            if self.type == NodeType.ARRAY:
                child = self.children[-1]
            else:
                child = self.children[self.last_key]

            self.file.seek(child.end_position())

            if not self.skip_comma():
                if expecting_next:
                    if self.type == NodeType.ARRAY:
                        raise IndexError('Array index out of range')
                    else:
                        raise KeyError('Key not found')

                return True
            else:
                return False

    def read_next_array_child(self, expecting_next) -> Union[None, Node]:
        # If we already know the size of the array, there are no more items
        if self.size is not None:
            if expecting_next:
                raise IndexError('Array index out of range')
            else:
                return None

        must_end = self.seek_next_child(expecting_next)

        if must_end and self.peek(1) != b']':
            buf = self.peek(10)

            raise ValueError(f'Unexpected input: {buf}')

        if self.peek(1) == b']':
            self.size = len(self.children)

            self.end = self.file.tell() + 1

            if expecting_next:
                raise IndexError('Array index out of range')
            else:
                return None

        child = Node(self.file, self.file.tell())

        self.children.append(child)

        return child

    def read_array_children_up_to(self, amount: Union[int, None]):
        # If we already know the necessary amount of children, do nothing
        if amount is not None and amount <= len(self.children):
            return

        # Keep reading children until we get to the one we want or we find the
        # end of the JSON array
        while True:
            child = self.read_next_array_child(amount is not None)

            if amount is None and child is None:
                # We have successfully read all children
                return

            if len(self.children) == amount:
                # We have found as many children as requested; in this case
                # there is no need to find out the length of this child
                return

    def read_object_children_up_to(self, key: Union[str, None]):
        # If we already know this key, do nothing
        if key in self.children:
            return

        # Keep reading children until we get to the one we want or we find the
        # end of the JSON object
        while True:
            child = self.read_next_object_child(key is not None)

            if key is None and child is None:
                # We have successfully read all children
                return

            if key in self.children:
                # We have found as many children as requested; in this case
                # there is no need to find out the length of this child
                return

    def read_next_object_child(self, expecting_next):
        # If we already know the size of the array, there are no more items
        if self.size is not None:
            if expecting_next:
                raise KeyError(f'Key not found')
            else:
                return None

        self.seek_next_child(expecting_next)

        if self.peek(1) == b'}':
            self.size = len(self.children)

            self.end = self.file.tell() + 1

            if expecting_next:
                raise KeyError(f'Key not found')
            else:
                return None

        # We need to read a string. This string will not be a real node, but
        # we treat it as such here because it greatly simplifies the code,
        # even though it will probably use more memory than strictly needed.
        # But its use is temporary anyway, so this shouldn't be much of a
        # problem.
        this_key = Node(self.file, self.file.tell())

        if this_key.type != NodeType.STRING:
            raise ValueError(f'Cannot use {this_key.type} as object key')

        pos = this_key.end_position()  # TODO: Can it move down?

        this_key = this_key.value()

        self.file.seek(pos)

        if not self.skip_colon():
            raise ValueError('Expecting a colon')

        child = Node(self.file, self.file.tell())

        self.children[this_key] = child
        self.last_key = this_key

        return child

    def __getitem__(self, key):
        if self.type not in [NodeType.OBJECT, NodeType.ARRAY]:
            raise ValueError(f'Cannot index values of type {self.type}')

        if self.type == NodeType.ARRAY:
            if not isinstance(key, int):
                raise ValueError(
                    f'Can only index arrays with integers, not {type(key)}'
                )

            if key < 0:
                self.read_array_children_up_to(None)
            else:
                self.read_array_children_up_to(key + 1)

            return self.children[key]

        elif self.type == NodeType.OBJECT:
            if not isinstance(key, str):
                raise ValueError(
                    f'Can only index objects with strings, not {type(key)}'
                )

            self.read_object_children_up_to(key)

            return self.children[key]

    def __len__(self):
        if self.type not in [NodeType.OBJECT, NodeType.ARRAY]:
            raise ValueError(
                f'Cannot measure the length of values of type {self.type}'
            )

        if self.type == NodeType.ARRAY:
            self.read_array_children_up_to(None)
        elif self.type == NodeType.OBJECT:
            self.read_object_children_up_to(None)

        return len(self.children)

    def __iter__(self):
        if self.type not in [NodeType.OBJECT, NodeType.ARRAY]:
            raise ValueError(
                f'Cannot iterate over a value of type {self.type}'
            )

        if self.type == NodeType.ARRAY:
            yield from self.children

            while True:
                child = self.read_next_array_child(False)

                if child is not None:
                    yield child
                else:
                    return

        elif self.type == NodeType.OBJECT:
            yield from self.children

            while True:
                child = self.read_next_object_child(False)

                if child is not None:
                    yield self.last_key
                else:
                    return

    def keys(self):
        if self.type != NodeType.OBJECT:
            raise ValueError(
                f'Cannot get keys of values of type {self.type}'
            )

        return iter(self)

    def parse_string(self):
        self.file.seek(self.pos)

        length = self.compute_value_length()

        self.file.seek(self.pos)

        string = self.peek(length)

        parts = []

        prev = 1
        while True:
            backslash = string.find(b'\\', prev)

            if backslash == -1:
                parts.append(string[prev:-1].decode('utf8'))
                break

            parts.append(string[prev:backslash].decode('utf8'))

            next_char = string[backslash + 1:backslash + 2]

            MAP = {
                b'"': '"',
                b'\\': '\\',
                b'/': '/',
                b'b': '\b',
                b'f': '\f',
                b'n': '\n',
                b'r': '\r',
                b't': '\t',
            }

            escaped = MAP.get(next_char, None)

            if escaped is not None:
                parts.append(escaped)
            elif next_char == b'u':
                codepoint = int(string[backslash + 2:backslash + 6], 16)
                parts.append(chr(codepoint))
            else:
                raise ValueError(f'Unknown escaped sequence: \\{next_char}')

            prev = backslash + 2

        return ''.join(parts)

    def parse_number(self):
        length = self.compute_value_length()

        self.file.seek(self.pos)

        string = self.peek(length)

        return float(string)


def measure_string(file: BinaryIO, pos: int):
    file.seek(pos + 1)  # Skip the start quote

    result = 1

    while True:
        buf = file.read(1024)

        if len(buf) == 0:
            raise ValueError('The string does not terminate')

        quote_pos = 0
        while True:
            quote_pos = buf.find(b'"', quote_pos)

            if quote_pos == -1:
                break
            elif buf[quote_pos - 1:quote_pos] == b'\\':
                # Skip this quote
                quote_pos += 1

                continue
            else:
                break

        if quote_pos == -1:
            # We did not find a quote, so we need to search longer
            if b'\n' in buf or b'\r' in buf:
                raise ValueError('End of line while scanning string')

            result += len(buf)
            continue

        break

    buf = buf[:quote_pos]

    if b'\n' in buf or b'\r' in buf:
        raise ValueError('End of line while scanning string')

    # We must include the quote in the length of the string
    result += quote_pos + 1

    return result


def measure_number(file: BinaryIO, pos: int):
    # Grab all valid number characters and parse the result

    file.seek(pos)

    accumulated = []

    while True:
        # TODO: I must ensure that the file is actually buffered, or else this
        # line, reading one character at a time, will take an unnecessary long
        # time to run
        c = file.read(1)

        if c == b'':
            break
        elif c in b'-+0123456789eE.':
            accumulated.append(c)
        else:
            break

    accumulated = b''.join(accumulated)

    m = NUMBER_REGEX.match(accumulated)

    if m is None:
        raise ValueError(
            f'Number starts with a wrong character {accumulated[0]}'
        )

    return m.end()
