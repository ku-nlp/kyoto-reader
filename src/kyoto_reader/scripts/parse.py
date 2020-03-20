import string


class Parser:
    DELIMITERS = string.whitespace

    def __init__(self, string_: str):
        self.string = string_
        self.pos = 0

    @classmethod
    def from_file(cls, path: str):
        return cls(open(path).read())

    def peek(self):
        return self.string[self.pos]

    def pop(self):
        c = self.string[self.pos]
        self.pos += 1
        return c

    def read_list(self):
        elements = []
        while True:
            element = self.read()
            if element == ")":
                return elements
            elif element:
                elements.append(element)
        self.eof_error()

    @staticmethod
    def read_right_paren():
        return ")"

    def read_comment(self):
        char = self.pop()
        while char != "\n":
            char = self.pop()
        return self.read()

    def read_string(self):
        char = self.pop()
        string_ = ""
        while char is not "\"":
            string_ += char
            char = self.pop()
        return string_

    @property
    def read_table(self):
        return {
            "(": self.read_list,
            ")": self.read_right_paren,
            ";": self.read_comment,
            "\"": self.read_string,
        }

    def read(self):
        if self.pos == len(self.string):
            return []
        symbol = ""
        char = self.peek()
        while char:
            if char in self.read_table.keys():
                if symbol:
                    return symbol
                else:
                    return self.read_table[self.pop()]()
                # return symbol if symbol else read_table[read_char(stream)](stream)
            elif char in Parser.DELIMITERS:
                self.pop()
                return symbol
            else:
                symbol += self.pop()
            char = self.peek()
        self.eof_error()

    def eof_error(self):
        pos: int = self.pos + 1
        buf: str = self.string[:pos]
        row: int = buf.count("\n") + 1
        col: int = len("".join(buf).split("\n")[-1])
        # char: str = repr(buf[-1])

        raise EOFError(f"Unexpected EOF while reading string at file position {pos} (row: {row}, col: {col}).")

# from pprint import pprint
# if __name__ == "__main__":
#     file = 'test.dic' if len(sys.argv) < 2 else sys.argv[1]
#     with open(file) as f:
#         for line in f:
#             pprint(Parser(line).read())
