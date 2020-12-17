import sys
from antlr4 import *
from v1_2EcmaStringLexer import CwlEcmaStringLexer
from v1_2EcmaStringParser import CwlEcmaStringParser

def main(argv):
    inp = FileStream(argv[1])
    lexer = CwlEcmaStringLexer(inp)
    stream = CommonTokenStream(lexer)
    parser = CwlEcmaStringParser(stream)
    tree = parser.interpolated_string()

if __name__ == '__main__':
    main(sys.argv)

