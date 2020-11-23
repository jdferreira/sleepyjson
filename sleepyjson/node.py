from __future__ import annotations

from collections import deque
from enum import Enum, auto

from .parser import Parser, unescape_string_literal



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

# The maximum number of characters we need to read in order to determine this
# node's type
MAX_NEEDED_CHARS = 5


class Node:
    def __init__(self, file, pos):
        self.parser = Parser(file)

        self.pos = self.parser.skip_to_start(pos)

        self.end = None

        self.type = self.get_type()

    def get_type(self):
        buf = self.parser.read(self.pos, MAX_NEEDED_CHARS)

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
            literal = self.parser.read(self.pos, self.end_position() - self.pos)

            return unescape_string_literal(literal)
        elif self.type == NodeType.NUMBER:
            literal = self.parser.read(self.pos, self.end_position() - self.pos)

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
                self.end = self.pos + self.parser.measure_string(self.pos)
            elif self.type == NodeType.NUMBER:
                self.end = self.pos + self.parser.measure_number(self.pos)
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
        pos = self.pos + 1

        while True:
            next_child_start = self.parser.seek_next_array_child(pos)

            if next_child_start is not None:
                current_child = Node(self.parser.file, next_child_start)

                yield current_child

                self.parser.file.seek(current_child.end_position())

                if not self.parser.skip_comma():
                    break

                pos = self.parser.file.tell()
            else:
                self.end = self.parser.file.tell()

                return

    def items(self):
        if self.type != NodeType.OBJECT:
            raise ValueError(
                f'Cannot get keys of values of type {self.type}'
            )

        pos = self.pos + 1

        while True:
            object_item = self.parser.seek_next_object_child(pos)

            if object_item is not None:
                current_child = Node(self.parser.file, object_item[1])

                yield (object_item[0], current_child)

                self.parser.file.seek(current_child.end_position())

                self.parser.skip_comma()

                pos = self.parser.file.tell()
            else:
                self.end = self.parser.file.tell()

                return

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


