from .node import Node


class Reader:
    def __init__(self, file):
        self.top_node = Node(file, 0)

        self.node_positions = [0]
        self.stream_cursor = 0

    def __getattr__(self, name: str):
        return getattr(self.top_node, name)

    def __getitem__(self, key):
        return self.top_node[key]

    def __len__(self):
        return len(self.top_node)

    def next(self):
        end = self.top_node.end_position()

        self.top_node = Node(self.file, end + 1)

        self.stream_cursor += 1
        self.node_positions.append(end + 1)

    def prev(self):
        if self.stream_cursor == 0:
            raise IndexError('Reader is already at the start of the stream')

        self.stream_cursor -= 1
        self.top_node = Node(self.file, self.node_positions[self.stream_cursor])

    def seek(self, index):
        if index < 0:
            raise IndexError('Cannot seek to negative indices')

        if index < len(self.node_positions):
            self.stream_cursor = index
            self.top_node = Node(self.file, self.node_positions[self.stream_cursor])
            return

        while index >= len(self.node_positions):
            try:
                self.next()
            except ValueError:
                raise IndexError('Index out of bounds')

        return self.top_node

