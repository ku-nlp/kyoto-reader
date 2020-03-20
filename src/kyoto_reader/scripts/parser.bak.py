import sys
import string

def read_char(stream):
    return stream.read(1)

def peek_char(stream):
    pos = stream.tell()
    char = read_char(stream)
    stream.seek(pos)
    return char

def make_seekable_stream(stream):
    from io import StringIO
    if not stream.seekable():
        if hasattr(stream, "name"):
            name = stream.name if stream.name else repr(stream)
        else:
            name = repr(stream)
        stream = StringIO(stream.read())
        stream.name = name
        return stream
    return stream

def describe_stream(stream):
    position = stream.tell() + 1
    stream.seek(0)
    buf = [stream.read(1) for _ in range(position)]
    row = buf.count("\n") + 1
    col = len("".join(buf).split("\n")[-1])
    char = repr(buf[-1])

    return {
        "name": stream.name,
        "position": position,
        "row": row,
        "col": col,
        "char": char,
    }

def eof_error(stream):
    "Unexpected EOF while reading {name} at file position {position} (row: {row}, col: {col})."
    raise EOFError(eof_error.__doc__.format(**describe_stream(stream)))

def syntax_error(stream):
    "Invalid character {char} in {name} at file position {position} (row: {row}, col: {col})"
    raise SyntaxError(syntax_error.__doc__.format(**describe_stream(stream)))

def read_list(stream):
    elements = []
    element = read(stream)
    while element:
        if element is ")":
            return elements
        else:
            elements.append(element)
        element = read(stream)
    eof_error(stream)

def right_paren_reader(stream):
    return ")"

def read_comment(stream):
    char = peek_char(stream)
    while char is not "\n":
        read_char(stream)
        char = peek_char(stream)
    return read(stream)

def read_quote(stream):
    return ["quote", read(stream)]

readtable = {
    "(": read_list,
    ")": right_paren_reader,
    ";": read_comment,
    "'": read_quote,
}

delimiters = string.whitespace
validchars = string.ascii_letters + string.digits + "-+*/%=!?<>^&"

def read(stream=sys.stdin):
    symbol = ""
    stream = make_seekable_stream(stream)
    char = peek_char(stream)
    while char:
        print(char)
        if char in readtable.keys():
            return symbol if symbol else readtable[read_char(stream)](stream)
        elif char in delimiters:
            read_char(stream)
            if symbol:
                return symbol
        elif char in validchars:
            symbol += read_char(stream)
        else:
            syntax_error(stream)
        char = peek_char(stream)
    eof_error(stream)

if __name__ == "__main__":
    print(read())
