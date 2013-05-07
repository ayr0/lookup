'''
Created on Oct 15, 2012

@author: grout
'''

import string

class Parser(object):
    def __init__(self, ref_str, start_pos=0,):
        self.input = ' '.join(ref_str.split())
        self.pos = start_pos
        self.last = None
        self.end = len(self.input)-1
            
        
    def nextBrace(self, openbrace='{', closebrace='}'):
        self.pos, self.last = matchNextBrace(self.input, start=self.pos, openbrace=openbrace, closebrace=closebrace)
        self._whitespace()
        return self.last
        
    def nextLiteral(self, expected):
        self.pos = matchStr(self.input, expected, start=self.pos)
        self._whitespace()
        self.last = expected
        return self.last
    
    def nextWord(self, alphanum=False):
        self.pos, self.last = matchWord(self.input, start=self.pos, alphanum=alphanum)
        self._whitespace()
        return self.last
    
    def _whitespace(self):
        self.pos = matchWhitespace(self.input, start=self.pos)
        
    def subParser(self):
        self.sub = Parser(self.last)
        
        
def matchNextBrace(stream, start=0, openbrace="{", closebrace="}"):
    cnt = 0
    for ind in xrange(start, len(stream)):
        c = stream[ind]
        if c == openbrace:
            cnt += 1
        elif c == closebrace:
            cnt -= 1
        
        if cnt == 0:
            ret = stream[start+1:ind]
            return ind+1, ret.replace('\n', " ").strip()
        
def matchStr(s, expected, start=0):
    l = start+len(expected)
    cmp = s[start:l]
    if cmp == expected:
        return l
    else:
        raise ValueError("Unexpected String! Expected: {} but got {} instead!".format(expected, cmp))
    
def matchWord(s, start=0, alphanum=False):
    if alphanum:
        chars = string.letters+string.digits
    else:
        chars = string.letters
        
    for ind in xrange(start, len(s)):
        if s[ind] not in chars:
            return ind, s[start:ind]
        
def matchWhitespace(s, start=0):
    for ind in xrange(start, len(s)):
        if s[ind] not in string.whitespace:
            return ind
    return len(s)-1