from .node import Node


class Reader:
    def __init__(self, file):
        self.file = file
        self.pos = 0

    def __getitem__(self, key):
        return Node()
