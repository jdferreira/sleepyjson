import re
import sleepyjson.node as node

WHITESPACE = '\r\n\t '
BUF_LENGTH = 1024
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


class Parser:
    def __init__(self, file):
        if not file.seekable():
            raise ValueError('The file must be seekable')

        self.file = file

    def skip_to_start(self, pos):
        self.file.seek(pos)

        self.skip_skippable()

        return self.file.tell()

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

    def read(self, pos, n):
        self.file.seek(pos)

        buf = self.file.read(n)

        if not buf:
            raise ValueError('Unexpected end of file')

        return buf

    def seek_next_array_child(self, pos):
        self.file.seek(pos)

        next_char = self.peek(1)

        if next_char == '':
            raise ValueError(f'Unexpected end of file')
        elif next_char == ']':
            self.file.read(1)

            return None
        else:
            return self.file.tell()

    def seek_next_object_child(self, pos):
        self.file.seek(pos)

        next_char = self.peek(1)

        if next_char == '':
            raise ValueError(f'Unexpected end of file')
        elif next_char == '}':
            self.file.read(1)

            return None

        # We need to read a string. This string will not be a real node, but we
        # treat it as such here because it greatly simplifies the code, even
        # though it will probably use more memory than strictly needed. But its
        # use is temporary anyway, so this shouldn't be much of a problem.
        key = node.Node(self.file, self.file.tell())

        if key.type != node.NodeType.STRING:
            raise ValueError(f'Cannot use {key.type} as object key')

        self.file.seek(key.end_position())

        if not self.skip_colon():
            raise ValueError('Expecting a colon')

        # Hold on to current position as `key.value()` will change the cursor
        pos = self.file.tell()

        return (key.value(), pos)

    def measure_string(self, pos):
        self.file.seek(pos + 1)  # Skip the start quote

        result = 1
        prev_was_backslash = False

        while True:
            buf = self.file.read(BUF_LENGTH)

            if len(buf) == 0:
                raise ValueError('The string does not terminate')

            quote_pos = 0
            while True:
                quote_pos = buf.find('"', quote_pos)

                if quote_pos == -1:
                    break
                elif (quote_pos == 0 and prev_was_backslash) or buf[quote_pos - 1] == '\\':
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

                prev_was_backslash = buf[-1] == '\\'

                continue

            break

        buf = buf[:quote_pos]

        if '\n' in buf:
            raise ValueError('End of line while scanning string')

        result += len(buf) + 1

        return result

    def measure_number(self, pos):
        self.file.seek(pos)

        accumulated = []

        while True:
            buf = self.file.read(BUF_LENGTH)

            if not buf:
                break

            for i, c in enumerate(buf):
                if c not in '-+0123456789eE.':
                    break
            else:
                # We never broke from the for loop, which means that we may need
                # more characters
                accumulated.append(buf)

                continue

            accumulated.append(buf[:i])

            break

        accumulated = ''.join(accumulated)

        m = NUMBER_REGEX.match(accumulated)

        if m is None:
            raise ValueError(
                f'Number starts with a wrong character {accumulated[0]}'
            )

        return m.end()


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
                raise ValueError(
                    f'Truncated unicode escaped value: \\u{codepoint}')

            for i, c in enumerate(codepoint):
                if c not in '0123456789abcdefABCDEF':
                    hexadigis = codepoint[:i]

                    raise ValueError(
                        f'Truncated unicode escaped value: \\u{hexadigis}')

            codepoint = int(codepoint, 16)

            parts.append(chr(codepoint))

            prev = backslash + 6
        else:
            raise ValueError(f'Unknown escaped sequence: \\{next_char}')

    return ''.join(parts)
