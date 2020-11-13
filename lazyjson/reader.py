from .node import Node


class Reader(Node):
    def __init__(self, file):
        self.file = file
        self.pos = 0
