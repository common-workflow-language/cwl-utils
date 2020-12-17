# Generated from antlr4/CwlParameterReferenceParser.g4 by ANTLR 4.7.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
from typing.io import TextIO
import sys

def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3\30")
        buf.write("H\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7\4\b")
        buf.write("\t\b\4\t\t\t\3\2\3\2\3\2\3\3\3\3\3\3\3\3\3\4\3\4\3\5\3")
        buf.write("\5\6\5\36\n\5\r\5\16\5\37\3\5\3\5\3\5\3\5\6\5&\n\5\r\5")
        buf.write("\16\5\'\3\5\3\5\5\5,\n\5\3\6\3\6\3\6\5\6\61\n\6\3\7\3")
        buf.write("\7\3\7\7\7\66\n\7\f\7\16\79\13\7\3\7\3\7\3\b\3\b\3\b\3")
        buf.write("\b\5\bA\n\b\3\t\6\tD\n\t\r\t\16\tE\3\t\2\2\n\2\4\6\b\n")
        buf.write("\f\16\20\2\3\3\2\26\27\2I\2\22\3\2\2\2\4\25\3\2\2\2\6")
        buf.write("\31\3\2\2\2\b+\3\2\2\2\n\60\3\2\2\2\f\62\3\2\2\2\16@\3")
        buf.write("\2\2\2\20C\3\2\2\2\22\23\7\20\2\2\23\24\7\21\2\2\24\3")
        buf.write("\3\2\2\2\25\26\7\24\2\2\26\27\7\30\2\2\27\30\7\24\2\2")
        buf.write("\30\5\3\2\2\2\31\32\t\2\2\2\32\7\3\2\2\2\33\35\7\22\2")
        buf.write("\2\34\36\5\6\4\2\35\34\3\2\2\2\36\37\3\2\2\2\37\35\3\2")
        buf.write("\2\2\37 \3\2\2\2 !\3\2\2\2!\"\7\22\2\2\",\3\2\2\2#%\7")
        buf.write("\23\2\2$&\5\6\4\2%$\3\2\2\2&\'\3\2\2\2\'%\3\2\2\2\'(\3")
        buf.write("\2\2\2()\3\2\2\2)*\7\23\2\2*,\3\2\2\2+\33\3\2\2\2+#\3")
        buf.write("\2\2\2,\t\3\2\2\2-\61\5\2\2\2.\61\5\4\3\2/\61\5\b\5\2")
        buf.write("\60-\3\2\2\2\60.\3\2\2\2\60/\3\2\2\2\61\13\3\2\2\2\62")
        buf.write("\63\7\6\2\2\63\67\7\21\2\2\64\66\5\n\6\2\65\64\3\2\2\2")
        buf.write("\669\3\2\2\2\67\65\3\2\2\2\678\3\2\2\28:\3\2\2\29\67\3")
        buf.write("\2\2\2:;\7\25\2\2;\r\3\2\2\2<A\7\n\2\2=A\7\b\2\2>A\5\f")
        buf.write("\7\2?A\7\13\2\2@<\3\2\2\2@=\3\2\2\2@>\3\2\2\2@?\3\2\2")
        buf.write("\2A\17\3\2\2\2BD\5\16\b\2CB\3\2\2\2DE\3\2\2\2EC\3\2\2")
        buf.write("\2EF\3\2\2\2F\21\3\2\2\2\t\37\'+\60\67@E")
        return buf.getvalue()


class CwlParameterReferenceParser ( Parser ):

    grammarFileName = "CwlParameterReferenceParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'.'", "'['", "']'", "'$('", "')'", "'\\$('", 
                     "'\\'", "'\\\\'", "<INVALID>", "'[''", "'[\"'", "'']'", 
                     "'\"]'" ]

    symbolicNames = [ "<INVALID>", "DOT", "LBRACKET", "RBRACKET", "DOLLARPAREN", 
                      "RPAREN", "DOLLARPARENESC", "BACKSLASH", "BACKSLASHESC", 
                      "ANYCHAR", "LBRACKETSINGLEQ", "LBRACKETDOUBLEQ", "SINGLEQRBRACKET", 
                      "DOUBLEQRBRACKET", "ExprDot", "ExprSymbol", "ExprSingleQ", 
                      "ExprDoubleQ", "ExprIntIndex", "EndParenExpr", "StringIndexEscPart", 
                      "StringIndexPart", "IntIndexPart" ]

    RULE_expr_dot_symbol = 0
    RULE_int_index = 1
    RULE_string_index_part = 2
    RULE_string_index = 3
    RULE_expr_segment = 4
    RULE_paren_expr = 5
    RULE_interpolated_string_part = 6
    RULE_interpolated_string = 7

    ruleNames =  [ "expr_dot_symbol", "int_index", "string_index_part", 
                   "string_index", "expr_segment", "paren_expr", "interpolated_string_part", 
                   "interpolated_string" ]

    EOF = Token.EOF
    DOT=1
    LBRACKET=2
    RBRACKET=3
    DOLLARPAREN=4
    RPAREN=5
    DOLLARPARENESC=6
    BACKSLASH=7
    BACKSLASHESC=8
    ANYCHAR=9
    LBRACKETSINGLEQ=10
    LBRACKETDOUBLEQ=11
    SINGLEQRBRACKET=12
    DOUBLEQRBRACKET=13
    ExprDot=14
    ExprSymbol=15
    ExprSingleQ=16
    ExprDoubleQ=17
    ExprIntIndex=18
    EndParenExpr=19
    StringIndexEscPart=20
    StringIndexPart=21
    IntIndexPart=22

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.7.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None



    class Expr_dot_symbolContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ExprDot(self):
            return self.getToken(CwlParameterReferenceParser.ExprDot, 0)

        def ExprSymbol(self):
            return self.getToken(CwlParameterReferenceParser.ExprSymbol, 0)

        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_expr_dot_symbol

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpr_dot_symbol" ):
                listener.enterExpr_dot_symbol(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpr_dot_symbol" ):
                listener.exitExpr_dot_symbol(self)




    def expr_dot_symbol(self):

        localctx = CwlParameterReferenceParser.Expr_dot_symbolContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_expr_dot_symbol)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 16
            self.match(CwlParameterReferenceParser.ExprDot)
            self.state = 17
            self.match(CwlParameterReferenceParser.ExprSymbol)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Int_indexContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ExprIntIndex(self, i:int=None):
            if i is None:
                return self.getTokens(CwlParameterReferenceParser.ExprIntIndex)
            else:
                return self.getToken(CwlParameterReferenceParser.ExprIntIndex, i)

        def IntIndexPart(self):
            return self.getToken(CwlParameterReferenceParser.IntIndexPart, 0)

        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_int_index

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInt_index" ):
                listener.enterInt_index(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInt_index" ):
                listener.exitInt_index(self)




    def int_index(self):

        localctx = CwlParameterReferenceParser.Int_indexContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_int_index)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 19
            self.match(CwlParameterReferenceParser.ExprIntIndex)
            self.state = 20
            self.match(CwlParameterReferenceParser.IntIndexPart)
            self.state = 21
            self.match(CwlParameterReferenceParser.ExprIntIndex)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class String_index_partContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def StringIndexPart(self):
            return self.getToken(CwlParameterReferenceParser.StringIndexPart, 0)

        def StringIndexEscPart(self):
            return self.getToken(CwlParameterReferenceParser.StringIndexEscPart, 0)

        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_string_index_part

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterString_index_part" ):
                listener.enterString_index_part(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitString_index_part" ):
                listener.exitString_index_part(self)




    def string_index_part(self):

        localctx = CwlParameterReferenceParser.String_index_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_string_index_part)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 23
            _la = self._input.LA(1)
            if not(_la==CwlParameterReferenceParser.StringIndexEscPart or _la==CwlParameterReferenceParser.StringIndexPart):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class String_indexContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ExprSingleQ(self, i:int=None):
            if i is None:
                return self.getTokens(CwlParameterReferenceParser.ExprSingleQ)
            else:
                return self.getToken(CwlParameterReferenceParser.ExprSingleQ, i)

        def string_index_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlParameterReferenceParser.String_index_partContext)
            else:
                return self.getTypedRuleContext(CwlParameterReferenceParser.String_index_partContext,i)


        def ExprDoubleQ(self, i:int=None):
            if i is None:
                return self.getTokens(CwlParameterReferenceParser.ExprDoubleQ)
            else:
                return self.getToken(CwlParameterReferenceParser.ExprDoubleQ, i)

        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_string_index

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterString_index" ):
                listener.enterString_index(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitString_index" ):
                listener.exitString_index(self)




    def string_index(self):

        localctx = CwlParameterReferenceParser.String_indexContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_string_index)
        self._la = 0 # Token type
        try:
            self.state = 41
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlParameterReferenceParser.ExprSingleQ]:
                self.enterOuterAlt(localctx, 1)
                self.state = 25
                self.match(CwlParameterReferenceParser.ExprSingleQ)
                self.state = 27 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 26
                    self.string_index_part()
                    self.state = 29 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==CwlParameterReferenceParser.StringIndexEscPart or _la==CwlParameterReferenceParser.StringIndexPart):
                        break

                self.state = 31
                self.match(CwlParameterReferenceParser.ExprSingleQ)
                pass
            elif token in [CwlParameterReferenceParser.ExprDoubleQ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 33
                self.match(CwlParameterReferenceParser.ExprDoubleQ)
                self.state = 35 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 34
                    self.string_index_part()
                    self.state = 37 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==CwlParameterReferenceParser.StringIndexEscPart or _la==CwlParameterReferenceParser.StringIndexPart):
                        break

                self.state = 39
                self.match(CwlParameterReferenceParser.ExprDoubleQ)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Expr_segmentContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr_dot_symbol(self):
            return self.getTypedRuleContext(CwlParameterReferenceParser.Expr_dot_symbolContext,0)


        def int_index(self):
            return self.getTypedRuleContext(CwlParameterReferenceParser.Int_indexContext,0)


        def string_index(self):
            return self.getTypedRuleContext(CwlParameterReferenceParser.String_indexContext,0)


        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_expr_segment

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpr_segment" ):
                listener.enterExpr_segment(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpr_segment" ):
                listener.exitExpr_segment(self)




    def expr_segment(self):

        localctx = CwlParameterReferenceParser.Expr_segmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_expr_segment)
        try:
            self.state = 46
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlParameterReferenceParser.ExprDot]:
                self.enterOuterAlt(localctx, 1)
                self.state = 43
                self.expr_dot_symbol()
                pass
            elif token in [CwlParameterReferenceParser.ExprIntIndex]:
                self.enterOuterAlt(localctx, 2)
                self.state = 44
                self.int_index()
                pass
            elif token in [CwlParameterReferenceParser.ExprSingleQ, CwlParameterReferenceParser.ExprDoubleQ]:
                self.enterOuterAlt(localctx, 3)
                self.state = 45
                self.string_index()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Paren_exprContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DOLLARPAREN(self):
            return self.getToken(CwlParameterReferenceParser.DOLLARPAREN, 0)

        def ExprSymbol(self):
            return self.getToken(CwlParameterReferenceParser.ExprSymbol, 0)

        def EndParenExpr(self):
            return self.getToken(CwlParameterReferenceParser.EndParenExpr, 0)

        def expr_segment(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlParameterReferenceParser.Expr_segmentContext)
            else:
                return self.getTypedRuleContext(CwlParameterReferenceParser.Expr_segmentContext,i)


        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_paren_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParen_expr" ):
                listener.enterParen_expr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParen_expr" ):
                listener.exitParen_expr(self)




    def paren_expr(self):

        localctx = CwlParameterReferenceParser.Paren_exprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_paren_expr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 48
            self.match(CwlParameterReferenceParser.DOLLARPAREN)
            self.state = 49
            self.match(CwlParameterReferenceParser.ExprSymbol)
            self.state = 53
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << CwlParameterReferenceParser.ExprDot) | (1 << CwlParameterReferenceParser.ExprSingleQ) | (1 << CwlParameterReferenceParser.ExprDoubleQ) | (1 << CwlParameterReferenceParser.ExprIntIndex))) != 0):
                self.state = 50
                self.expr_segment()
                self.state = 55
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 56
            self.match(CwlParameterReferenceParser.EndParenExpr)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Interpolated_string_partContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def BACKSLASHESC(self):
            return self.getToken(CwlParameterReferenceParser.BACKSLASHESC, 0)

        def DOLLARPARENESC(self):
            return self.getToken(CwlParameterReferenceParser.DOLLARPARENESC, 0)

        def paren_expr(self):
            return self.getTypedRuleContext(CwlParameterReferenceParser.Paren_exprContext,0)


        def ANYCHAR(self):
            return self.getToken(CwlParameterReferenceParser.ANYCHAR, 0)

        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_interpolated_string_part

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInterpolated_string_part" ):
                listener.enterInterpolated_string_part(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInterpolated_string_part" ):
                listener.exitInterpolated_string_part(self)




    def interpolated_string_part(self):

        localctx = CwlParameterReferenceParser.Interpolated_string_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_interpolated_string_part)
        try:
            self.state = 62
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlParameterReferenceParser.BACKSLASHESC]:
                self.enterOuterAlt(localctx, 1)
                self.state = 58
                self.match(CwlParameterReferenceParser.BACKSLASHESC)
                pass
            elif token in [CwlParameterReferenceParser.DOLLARPARENESC]:
                self.enterOuterAlt(localctx, 2)
                self.state = 59
                self.match(CwlParameterReferenceParser.DOLLARPARENESC)
                pass
            elif token in [CwlParameterReferenceParser.DOLLARPAREN]:
                self.enterOuterAlt(localctx, 3)
                self.state = 60
                self.paren_expr()
                pass
            elif token in [CwlParameterReferenceParser.ANYCHAR]:
                self.enterOuterAlt(localctx, 4)
                self.state = 61
                self.match(CwlParameterReferenceParser.ANYCHAR)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Interpolated_stringContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def interpolated_string_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlParameterReferenceParser.Interpolated_string_partContext)
            else:
                return self.getTypedRuleContext(CwlParameterReferenceParser.Interpolated_string_partContext,i)


        def getRuleIndex(self):
            return CwlParameterReferenceParser.RULE_interpolated_string

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInterpolated_string" ):
                listener.enterInterpolated_string(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInterpolated_string" ):
                listener.exitInterpolated_string(self)




    def interpolated_string(self):

        localctx = CwlParameterReferenceParser.Interpolated_stringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_interpolated_string)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 65 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 64
                self.interpolated_string_part()
                self.state = 67 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << CwlParameterReferenceParser.DOLLARPAREN) | (1 << CwlParameterReferenceParser.DOLLARPARENESC) | (1 << CwlParameterReferenceParser.BACKSLASHESC) | (1 << CwlParameterReferenceParser.ANYCHAR))) != 0)):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





