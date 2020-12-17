# Generated from antlr4/CwlEcmaStringParser.g4 by ANTLR 4.7.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
from typing.io import TextIO
import sys

def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3\24")
        buf.write("K\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7\4\b")
        buf.write("\t\b\4\t\t\t\3\2\3\2\7\2\25\n\2\f\2\16\2\30\13\2\3\2\3")
        buf.write("\2\3\3\3\3\5\3\36\n\3\3\4\3\4\7\4\"\n\4\f\4\16\4%\13\4")
        buf.write("\3\4\3\4\3\5\3\5\3\5\5\5,\n\5\3\6\3\6\6\6\60\n\6\r\6\16")
        buf.write("\6\61\3\6\3\6\3\7\3\7\6\78\n\7\r\7\16\79\3\7\3\7\3\b\3")
        buf.write("\b\3\b\3\b\3\b\3\b\5\bD\n\b\3\t\6\tG\n\t\r\t\16\tH\3\t")
        buf.write("\2\2\n\2\4\6\b\n\f\16\20\2\2\2O\2\22\3\2\2\2\4\35\3\2")
        buf.write("\2\2\6\37\3\2\2\2\b+\3\2\2\2\n-\3\2\2\2\f\65\3\2\2\2\16")
        buf.write("C\3\2\2\2\20F\3\2\2\2\22\26\7\22\2\2\23\25\5\4\3\2\24")
        buf.write("\23\3\2\2\2\25\30\3\2\2\2\26\24\3\2\2\2\26\27\3\2\2\2")
        buf.write("\27\31\3\2\2\2\30\26\3\2\2\2\31\32\7\23\2\2\32\3\3\2\2")
        buf.write("\2\33\36\7\24\2\2\34\36\5\2\2\2\35\33\3\2\2\2\35\34\3")
        buf.write("\2\2\2\36\5\3\2\2\2\37#\7\17\2\2 \"\5\4\3\2! \3\2\2\2")
        buf.write("\"%\3\2\2\2#!\3\2\2\2#$\3\2\2\2$&\3\2\2\2%#\3\2\2\2&\'")
        buf.write("\7\23\2\2\'\7\3\2\2\2(,\7\21\2\2),\7\16\2\2*,\5\6\4\2")
        buf.write("+(\3\2\2\2+)\3\2\2\2+*\3\2\2\2,\t\3\2\2\2-/\7\4\2\2.\60")
        buf.write("\5\b\5\2/.\3\2\2\2\60\61\3\2\2\2\61/\3\2\2\2\61\62\3\2")
        buf.write("\2\2\62\63\3\2\2\2\63\64\7\20\2\2\64\13\3\2\2\2\65\67")
        buf.write("\7\7\2\2\668\5\b\5\2\67\66\3\2\2\289\3\2\2\29\67\3\2\2")
        buf.write("\29:\3\2\2\2:;\3\2\2\2;<\7\20\2\2<\r\3\2\2\2=D\7\r\2\2")
        buf.write(">D\7\n\2\2?D\7\13\2\2@D\5\n\6\2AD\5\f\7\2BD\7\3\2\2C=")
        buf.write("\3\2\2\2C>\3\2\2\2C?\3\2\2\2C@\3\2\2\2CA\3\2\2\2CB\3\2")
        buf.write("\2\2D\17\3\2\2\2EG\5\16\b\2FE\3\2\2\2GH\3\2\2\2HF\3\2")
        buf.write("\2\2HI\3\2\2\2I\21\3\2\2\2\n\26\35#+\619CH")
        return buf.getvalue()


class CwlEcmaStringParser ( Parser ):

    grammarFileName = "CwlEcmaStringParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "'$('", "'('", "')'", "'${'", 
                     "'{'", "'}'", "'\\$('", "'\\${'", "'\\'", "'\\\\'" ]

    symbolicNames = [ "<INVALID>", "ANYCHAR", "DOLLARPAREN", "LPAREN", "RPAREN", 
                      "DOLLARBRACE", "LBRACE", "RBRACE", "DOLLARPARENESC", 
                      "DOLLARBRACEESC", "BACKSLASH", "BACKSLASHESC", "EscPart", 
                      "SubExprStart", "ExprEnd", "ExprPart", "SubSubExprStart", 
                      "SubExprEnd", "SubExprPart" ]

    RULE_sub_sub_expr = 0
    RULE_sub_expr_part = 1
    RULE_sub_expr = 2
    RULE_expr_part = 3
    RULE_paren_expr = 4
    RULE_brace_expr = 5
    RULE_interpolated_string_part = 6
    RULE_interpolated_string = 7

    ruleNames =  [ "sub_sub_expr", "sub_expr_part", "sub_expr", "expr_part", 
                   "paren_expr", "brace_expr", "interpolated_string_part", 
                   "interpolated_string" ]

    EOF = Token.EOF
    ANYCHAR=1
    DOLLARPAREN=2
    LPAREN=3
    RPAREN=4
    DOLLARBRACE=5
    LBRACE=6
    RBRACE=7
    DOLLARPARENESC=8
    DOLLARBRACEESC=9
    BACKSLASH=10
    BACKSLASHESC=11
    EscPart=12
    SubExprStart=13
    ExprEnd=14
    ExprPart=15
    SubSubExprStart=16
    SubExprEnd=17
    SubExprPart=18

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.7.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None



    class Sub_sub_exprContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SubSubExprStart(self):
            return self.getToken(CwlEcmaStringParser.SubSubExprStart, 0)

        def SubExprEnd(self):
            return self.getToken(CwlEcmaStringParser.SubExprEnd, 0)

        def sub_expr_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlEcmaStringParser.Sub_expr_partContext)
            else:
                return self.getTypedRuleContext(CwlEcmaStringParser.Sub_expr_partContext,i)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_sub_sub_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSub_sub_expr" ):
                listener.enterSub_sub_expr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSub_sub_expr" ):
                listener.exitSub_sub_expr(self)




    def sub_sub_expr(self):

        localctx = CwlEcmaStringParser.Sub_sub_exprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_sub_sub_expr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 16
            self.match(CwlEcmaStringParser.SubSubExprStart)
            self.state = 20
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==CwlEcmaStringParser.SubSubExprStart or _la==CwlEcmaStringParser.SubExprPart:
                self.state = 17
                self.sub_expr_part()
                self.state = 22
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 23
            self.match(CwlEcmaStringParser.SubExprEnd)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Sub_expr_partContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SubExprPart(self):
            return self.getToken(CwlEcmaStringParser.SubExprPart, 0)

        def sub_sub_expr(self):
            return self.getTypedRuleContext(CwlEcmaStringParser.Sub_sub_exprContext,0)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_sub_expr_part

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSub_expr_part" ):
                listener.enterSub_expr_part(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSub_expr_part" ):
                listener.exitSub_expr_part(self)




    def sub_expr_part(self):

        localctx = CwlEcmaStringParser.Sub_expr_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_sub_expr_part)
        try:
            self.state = 27
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlEcmaStringParser.SubExprPart]:
                self.enterOuterAlt(localctx, 1)
                self.state = 25
                self.match(CwlEcmaStringParser.SubExprPart)
                pass
            elif token in [CwlEcmaStringParser.SubSubExprStart]:
                self.enterOuterAlt(localctx, 2)
                self.state = 26
                self.sub_sub_expr()
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

    class Sub_exprContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def SubExprStart(self):
            return self.getToken(CwlEcmaStringParser.SubExprStart, 0)

        def SubExprEnd(self):
            return self.getToken(CwlEcmaStringParser.SubExprEnd, 0)

        def sub_expr_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlEcmaStringParser.Sub_expr_partContext)
            else:
                return self.getTypedRuleContext(CwlEcmaStringParser.Sub_expr_partContext,i)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_sub_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterSub_expr" ):
                listener.enterSub_expr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitSub_expr" ):
                listener.exitSub_expr(self)




    def sub_expr(self):

        localctx = CwlEcmaStringParser.Sub_exprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_sub_expr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 29
            self.match(CwlEcmaStringParser.SubExprStart)
            self.state = 33
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==CwlEcmaStringParser.SubSubExprStart or _la==CwlEcmaStringParser.SubExprPart:
                self.state = 30
                self.sub_expr_part()
                self.state = 35
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 36
            self.match(CwlEcmaStringParser.SubExprEnd)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Expr_partContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ExprPart(self):
            return self.getToken(CwlEcmaStringParser.ExprPart, 0)

        def EscPart(self):
            return self.getToken(CwlEcmaStringParser.EscPart, 0)

        def sub_expr(self):
            return self.getTypedRuleContext(CwlEcmaStringParser.Sub_exprContext,0)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_expr_part

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterExpr_part" ):
                listener.enterExpr_part(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitExpr_part" ):
                listener.exitExpr_part(self)




    def expr_part(self):

        localctx = CwlEcmaStringParser.Expr_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_expr_part)
        try:
            self.state = 41
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlEcmaStringParser.ExprPart]:
                self.enterOuterAlt(localctx, 1)
                self.state = 38
                self.match(CwlEcmaStringParser.ExprPart)
                pass
            elif token in [CwlEcmaStringParser.EscPart]:
                self.enterOuterAlt(localctx, 2)
                self.state = 39
                self.match(CwlEcmaStringParser.EscPart)
                pass
            elif token in [CwlEcmaStringParser.SubExprStart]:
                self.enterOuterAlt(localctx, 3)
                self.state = 40
                self.sub_expr()
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
            return self.getToken(CwlEcmaStringParser.DOLLARPAREN, 0)

        def ExprEnd(self):
            return self.getToken(CwlEcmaStringParser.ExprEnd, 0)

        def expr_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlEcmaStringParser.Expr_partContext)
            else:
                return self.getTypedRuleContext(CwlEcmaStringParser.Expr_partContext,i)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_paren_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterParen_expr" ):
                listener.enterParen_expr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitParen_expr" ):
                listener.exitParen_expr(self)




    def paren_expr(self):

        localctx = CwlEcmaStringParser.Paren_exprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_paren_expr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 43
            self.match(CwlEcmaStringParser.DOLLARPAREN)
            self.state = 45 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 44
                self.expr_part()
                self.state = 47 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << CwlEcmaStringParser.EscPart) | (1 << CwlEcmaStringParser.SubExprStart) | (1 << CwlEcmaStringParser.ExprPart))) != 0)):
                    break

            self.state = 49
            self.match(CwlEcmaStringParser.ExprEnd)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Brace_exprContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DOLLARBRACE(self):
            return self.getToken(CwlEcmaStringParser.DOLLARBRACE, 0)

        def ExprEnd(self):
            return self.getToken(CwlEcmaStringParser.ExprEnd, 0)

        def expr_part(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(CwlEcmaStringParser.Expr_partContext)
            else:
                return self.getTypedRuleContext(CwlEcmaStringParser.Expr_partContext,i)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_brace_expr

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterBrace_expr" ):
                listener.enterBrace_expr(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitBrace_expr" ):
                listener.exitBrace_expr(self)




    def brace_expr(self):

        localctx = CwlEcmaStringParser.Brace_exprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_brace_expr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 51
            self.match(CwlEcmaStringParser.DOLLARBRACE)
            self.state = 53 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 52
                self.expr_part()
                self.state = 55 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << CwlEcmaStringParser.EscPart) | (1 << CwlEcmaStringParser.SubExprStart) | (1 << CwlEcmaStringParser.ExprPart))) != 0)):
                    break

            self.state = 57
            self.match(CwlEcmaStringParser.ExprEnd)
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
            return self.getToken(CwlEcmaStringParser.BACKSLASHESC, 0)

        def DOLLARPARENESC(self):
            return self.getToken(CwlEcmaStringParser.DOLLARPARENESC, 0)

        def DOLLARBRACEESC(self):
            return self.getToken(CwlEcmaStringParser.DOLLARBRACEESC, 0)

        def paren_expr(self):
            return self.getTypedRuleContext(CwlEcmaStringParser.Paren_exprContext,0)


        def brace_expr(self):
            return self.getTypedRuleContext(CwlEcmaStringParser.Brace_exprContext,0)


        def ANYCHAR(self):
            return self.getToken(CwlEcmaStringParser.ANYCHAR, 0)

        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_interpolated_string_part

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInterpolated_string_part" ):
                listener.enterInterpolated_string_part(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInterpolated_string_part" ):
                listener.exitInterpolated_string_part(self)




    def interpolated_string_part(self):

        localctx = CwlEcmaStringParser.Interpolated_string_partContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_interpolated_string_part)
        try:
            self.state = 65
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [CwlEcmaStringParser.BACKSLASHESC]:
                self.enterOuterAlt(localctx, 1)
                self.state = 59
                self.match(CwlEcmaStringParser.BACKSLASHESC)
                pass
            elif token in [CwlEcmaStringParser.DOLLARPARENESC]:
                self.enterOuterAlt(localctx, 2)
                self.state = 60
                self.match(CwlEcmaStringParser.DOLLARPARENESC)
                pass
            elif token in [CwlEcmaStringParser.DOLLARBRACEESC]:
                self.enterOuterAlt(localctx, 3)
                self.state = 61
                self.match(CwlEcmaStringParser.DOLLARBRACEESC)
                pass
            elif token in [CwlEcmaStringParser.DOLLARPAREN]:
                self.enterOuterAlt(localctx, 4)
                self.state = 62
                self.paren_expr()
                pass
            elif token in [CwlEcmaStringParser.DOLLARBRACE]:
                self.enterOuterAlt(localctx, 5)
                self.state = 63
                self.brace_expr()
                pass
            elif token in [CwlEcmaStringParser.ANYCHAR]:
                self.enterOuterAlt(localctx, 6)
                self.state = 64
                self.match(CwlEcmaStringParser.ANYCHAR)
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
                return self.getTypedRuleContexts(CwlEcmaStringParser.Interpolated_string_partContext)
            else:
                return self.getTypedRuleContext(CwlEcmaStringParser.Interpolated_string_partContext,i)


        def getRuleIndex(self):
            return CwlEcmaStringParser.RULE_interpolated_string

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterInterpolated_string" ):
                listener.enterInterpolated_string(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitInterpolated_string" ):
                listener.exitInterpolated_string(self)




    def interpolated_string(self):

        localctx = CwlEcmaStringParser.Interpolated_stringContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_interpolated_string)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 68 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 67
                self.interpolated_string_part()
                self.state = 70 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & ((1 << CwlEcmaStringParser.ANYCHAR) | (1 << CwlEcmaStringParser.DOLLARPAREN) | (1 << CwlEcmaStringParser.DOLLARBRACE) | (1 << CwlEcmaStringParser.DOLLARPARENESC) | (1 << CwlEcmaStringParser.DOLLARBRACEESC) | (1 << CwlEcmaStringParser.BACKSLASHESC))) != 0)):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





