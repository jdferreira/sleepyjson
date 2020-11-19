from .node import Node


class Reader:
    def __init__(self, files):
        ft = file_type(files)

        if ft == '':
            self.files = iter([files])
        elif ft == b'':
            raise ValueError('Needs a text file')
        else:
            self.files = iter(files)

        self.current_file = next(self.files)
        self.next_file = False

        self.node = Node(self.current_file, 0)

    def __getattr__(self, name: str):
        return getattr(self.node, name)

    def __getitem__(self, key):
        return self.node[key]

    def __len__(self):
        return len(self.node)

    def __iter__(self):
        return iter(self.node)

    def next(self):
        if self.node_finishes_stream():
            self.current_file = next(self.files)

            if file_type(self.current_file) != '':
                raise ValueError('Needs a text file')

            pos = 0
        else:
            pos = self.node.end_position()

        self.node = Node(self.current_file, pos)

    def jump(self, n):
        if n < 0:
            raise ValueError('Cannot jump a negative amount of steps')

        for _ in range(n):
            self.next()

    def node_finishes_stream(self):
        self.node.file.seek(self.node.end_position())

        self.node.skip_skippable()

        return self.node.peek(1) == ''


def file_type(file):
    try:
        return file.read(0)
    except:
        return False

