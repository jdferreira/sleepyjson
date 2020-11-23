import random
import string
import os

def save_long_json(f, allow_comments=True, allow_trailing_comma=True):
    rand = random.Random(1337)

    def make_value(depth):
        if depth < 5:
            r = rand.randrange(100)
        else:
            r = rand.randrange(70)

        if r < 10:
            f.write('false')
        elif r < 20:
            f.write('true')
        elif r < 30:
            f.write('null')
        elif r < 50:
            make_number()
        elif r < 70:
            make_string('value')
        elif r < 85:
            make_array(depth)
        else:
            make_object(depth)

    def make_number():
        def make_digit_string(n):
            return ''.join(rand.choice(string.digits) for _ in range(rand.randrange(1, n + 1)))

        if rand.randrange(2) < 1:
            sign = '-'
        else:
            sign = ''

        integer = make_digit_string(6)

        integer = integer.lstrip('0')
        if not integer:
            integer = '0'

        if rand.randrange(2) < 1:
            decimal = '.' + make_digit_string(3)
        else:
            decimal = ''

        if rand.randrange(4) < 1:
            exponent = rand.choice('eE') + rand.choice(['+', '-', '']) + make_digit_string(2)
        else:
            exponent = ''

        f.write(sign + integer + decimal + exponent)

    def make_string(t):
        def make_char():
            r = rand.randrange(1000)

            if t == 'value' and r < 1:
                return '\\u00' + ''.join(rand.choice(string.hexdigits) for _ in range(2))
            elif t == 'value' and r < 2:
                return '\\t'
            elif t == 'value' and r < 3:
                return '\\r'
            elif t == 'value' and r < 4:
                return '\\r\\n'
            elif t == 'value' and r < 5:
                return '\\n'
            elif t == 'value' and r < 6:
                return '\\"'
            elif t in ['value', 'comment'] and r < 10:
                return rand.choice('.,')
            elif r < 20:
                return ' '
            else:
                return rand.choice(string.ascii_letters)

        if t == 'key':
            length = rand.randrange(2, 15)
        elif t == 'comment':
            length = rand.randrange(2, 80)
        else:
            length = rand.randrange(10, 1000)

        result = ''.join(make_char() for _ in range(length))

        if t == 'comment':
            f.write('// ')
            f.write(result)
        else:
            f.write('"' + result + '"')

    def make_array(depth):
        def value(last):
            f.write('    ' * (depth + 1))

            if allow_comments and rand.randrange(10) < 1:
                make_string('comment')
            else:
                make_value(depth + 1)

                if not last or (allow_trailing_comma and rand.randrange(2) < 1):
                    f.write(',')

        length = rand.randrange(100)

        f.write('[\n')

        for i in range(length):
            value(i == length - 1)
            f.write('\n')

        f.write('    ' * depth + ']')

    def make_object(depth):
        def value(last):
            f.write('    ' * (depth + 1))

            if allow_comments and rand.randrange(10) < 1:
                make_string('comment')
            else:
                make_string('key')
                f.write(': ')
                make_value(depth + 1)

                if not last or (allow_trailing_comma and rand.randrange(2) < 1):
                    f.write(',')

        length = rand.randrange(35)

        f.write('{\n')

        for i in range(length):
            value(i == length - 1)
            f.write('\n')

        f.write('    ' * depth + '}')

    make_object(0)


def generate_big_json(filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            save_long_json(f, False, False)
