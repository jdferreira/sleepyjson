from __future__ import annotations

import re
from collections import deque
from enum import Enum, auto

NUMBER_REGEX = re.compile(
    r'''
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


ESCAPE_CHARACTERS_MAP = {
    '"': '"',
    '\\': '\\',
    '/': '/',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}


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

NUMBER_DETERMINANTS = '0123456789-'

WHITESPACE = '\r\n\t '

# The maximum number of characters we need to read in order to determine this
# node's type
MAX_NEEDED_CHARS = 5


class Node:
    def __init__(self, file, pos):
        self.file = file

        if not file.seekable():
            raise ValueError('Nodes need to be able to seek into the file')

        self.skip_to_start(pos)

        self.end = None

        self.type = self.get_type()

        if self.type in [NodeType.ARRAY, NodeType.OBJECT]:
            self.current_child = None

    def skip_to_start(self, pos):
        self.file.seek(pos)

        self.skip_skippable()

        self.pos = self.file.tell()

    def skip_skippable(self):
        in_comment = False

        while True:
            c = self.file.read(1)

            if c == '':
                return

            if in_comment:
                if c == '\n':
                    in_comment = False
                continue

            if c in WHITESPACE:
                continue

            if c == '/':
                pos = self.file.tell()
                next_c = self.file.read(1)

                if next_c != '/':
                    self.file.seek(pos)
                else:
                    in_comment = True

                continue

            break

        self.file.seek(self.file.tell() - 1)

    def skip_comma(self):
        self.skip_skippable()

        if self.peek(1) == ',':
            self.file.read(1)

            self.skip_skippable()

            return True
        else:
            return False

    def skip_colon(self):
        self.skip_skippable()

        if self.peek(1) == ':':
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

        if any(buf[0] == c for c in NUMBER_DETERMINANTS):
            return NodeType.NUMBER

        raise ValueError(f'Unexpected input: {buf[:10]!r}')

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

    def value(self):
        if self.type == NodeType.TRUE:
            return True
        elif self.type == NodeType.FALSE:
            return False
        elif self.type == NodeType.NULL:
            return None
        elif self.type == NodeType.STRING:
            length = self.end_position() - self.pos

            self.file.seek(self.pos)

            literal = self.file.read(length)

            return unescape_string_literal(literal)
        elif self.type == NodeType.NUMBER:
            length = self.end_position() - self.pos

            self.file.seek(self.pos)

            literal = self.file.read(length)

            try:
                return int(literal)
            except ValueError:
                return float(literal)
        elif self.type == NodeType.ARRAY:
            return [child.value() for child in iter(self)]
        elif self.type == NodeType.OBJECT:
            return {key: child.value() for key, child in self.items()}

    def end_position(self):
        if self.end is None:
            if self.type == NodeType.TRUE:
                self.end = self.pos + 4
            elif self.type == NodeType.FALSE:
                self.end = self.pos + 5
            elif self.type == NodeType.NULL:
                self.end = self.pos + 4
            elif self.type == NodeType.STRING:
                self.end = self.pos + measure_string(self.file, self.pos)
            elif self.type == NodeType.NUMBER:
                self.end = self.pos + measure_number(self.file, self.pos)
            elif self.type in [NodeType.ARRAY, NodeType.OBJECT]:
                self.seek_to_end()

        return self.end

    def __getitem__(self, key):
        if self.type == NodeType.ARRAY:
            if not isinstance(key, int):
                raise ValueError(
                    f'Can only index arrays with integers, not {type(key)}'
                )

            if key < 0:
                queue = deque(self, -key)

                if len(queue) < -key:
                    raise IndexError('Array index out of bounds')
                else:
                    return queue[0]
            else:
                try:
                    # I'd like `iter(self).nth(i)` but it doesn't exist
                    return next(child for i, child in enumerate(self) if i == key)
                except StopIteration:
                    raise IndexError('Array index out of bounds')

        elif self.type == NodeType.OBJECT:
            if not isinstance(key, str):
                raise ValueError(
                    f'Can only index objects with strings, not {type(key)}'
                )

            try:
                return next(child for child_key, child in self.items() if child_key == key)
            except StopIteration:
                raise KeyError('Key not found')

        else:
            raise ValueError(f'Cannot index values of type {self.type}')

    def __len__(self):
        return sum(1 for _ in self)

    def __iter__(self):
        if self.type == NodeType.OBJECT:
            yield from (key for key, _ in self.items())
        elif self.type == NodeType.ARRAY:
            yield from self.array_iter()
        else:
            raise ValueError(
                f'Cannot iterate over a value of type {self.type}'
            )

    def array_iter(self):
        self.current_child = None

        self.file.seek(self.pos)

        while True:
            self.current_child = self.read_next_array_child()

            if self.current_child is not None:
                yield self.current_child
            else:
                return

    def items(self):
        if self.type != NodeType.OBJECT:
            raise ValueError(
                f'Cannot get keys of values of type {self.type}'
            )

        self.current_child = None

        self.file.seek(self.pos)

        while True:
            self.current_child = self.read_next_object_child()

            if self.current_child is not None:
                yield (self.last_key, self.current_child)
            else:
                return

    def read_next_array_child(self):
        must_end = self.seek_next_child()

        if must_end and self.peek(1) != ']':
            if self.peek(1) == '':
                raise ValueError(f'Unexpected end of file')
            else:
                raise ValueError(
                    f'Unexpected input {self.peek(10)!r} inside array')

        if self.peek(1) == ']':
            self.file.read(1)

            self.end = self.file.tell()

            return None

        return Node(self.file, self.file.tell())

    def read_next_object_child(self):
        must_end = self.seek_next_child()

        if must_end and self.peek(1) != '}':
            if self.peek(1) == '':
                raise ValueError(f'Unexpected end of file')
            else:
                raise ValueError(
                    f'Unexpected input {self.peek(10)!r} inside object')

        if self.peek(1) == '}':
            self.file.read(1)

            self.end = self.file.tell()

            return None

        # We need to read a string. This string will not be a real node, but we
        # treat it as such here because it greatly simplifies the code, even
        # though it will probably use more memory than strictly needed. But its
        # use is temporary anyway, so this shouldn't be much of a problem.
        this_key = Node(self.file, self.file.tell())

        if this_key.type != NodeType.STRING:
            raise ValueError(f'Cannot use {this_key.type} as object key')

        self.last_key = this_key.value()

        self.file.seek(this_key.end_position())

        if not self.skip_colon():
            raise ValueError('Expecting a colon')

        return Node(self.file, self.file.tell())

    def seek_next_child(self):
        if self.current_child is None:
            self.file.seek(self.pos + 1)

            self.skip_skippable()

            return False
        else:
            self.file.seek(self.current_child.end_position())

            return not self.skip_comma()

    def __contains__(self, item):
        if self.type == NodeType.ARRAY:
            return any(node.equals(item) for node in self)
        elif self.type == NodeType.OBJECT:
            return any(key == item for key in self)
        else:
            raise ValueError(
                f'Cannot iterate over a value of type {self.type}'
            )

    def equals(self, other):
        if self.type == NodeType.ARRAY:
            return all(left.equals(right) for left, right in zip(self, other))
        elif self.type == NodeType.OBJECT:
            sentinel = object()

            return all(lvalue.equals(other.get(lkey, sentinel)) for lkey, lvalue in self.items())
        else:
            return self.value() == other

    def seek_to_end(self):
        # Force a complete iteration on the value
        for _ in self:
            pass


def measure_string(file, pos):
    file.seek(pos + 1)  # Skip the start quote

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

    buf = buf[:quote_pos]

    if '\n' in buf:
        raise ValueError('End of line while scanning string')

    result += len(buf) + 1

    return result


def unescape_string_literal(literal):
    parts = []

    prev = 1
    while True:
        backslash = literal.find('\\', prev)

        if backslash == -1:
            parts.append(literal[prev:-1])
            break

        parts.append(literal[prev:backslash])

        next_char = literal[backslash + 1]

        escaped = ESCAPE_CHARACTERS_MAP.get(next_char, None)

        if escaped is not None:
            parts.append(escaped)

            prev = backslash + 2
        elif next_char == 'u':
            codepoint = literal[backslash + 2:backslash + 6]

            if len(codepoint) != 4:
                raise ValueError(f'Truncated unicode escaped value: \\u{codepoint}')

            for i, c in enumerate(codepoint):
                if c not in '0123456789abcdefABCDEF':
                    hexadigis = codepoint[:i]

                    raise ValueError(f'Truncated unicode escaped value: \\u{hexadigis}')

            codepoint = int(codepoint, 16)

            parts.append(chr(codepoint))

            prev = backslash + 6
        else:
            raise ValueError(f'Unknown escaped sequence: \\{next_char}')

    return ''.join(parts)


def measure_number(file, pos):
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
