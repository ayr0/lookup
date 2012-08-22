#Utility functions


import os
import RefObj
import fileinput
import itertools

def load_bib_lines(filenames, decomp=True):
    """Load *.tex files and read them line by line.
    This method only loads the bibliography section and checks for ascii"""
    
    bibliography = {}
    bibsection = 0
    biberrors = 0
    for line in fileinput.input(filenames):
        #iterate until we get to a bibitem section
        if line.startswith(r"\begin{thebibliography}"):
            #mark lines
            bibitems = []
            bibsection = 1
            continue
        elif line.startswith(r"\end{thebibliography}"):
            bibliography[fileinput.filename()] = bibitems
            bibitems = []
            bibsection = 0
            fileinput.nextfile()
        
        if bibsection == 1:
            if not line.isspace():
                try:
                    line = line.decode("ascii")
                    bibitems.append(line.strip())
                except UnicodeDecodeError:
                    print "Special Character on line {0} in file {1}".format(fileinput.filelineno(), fileinput.filename())
                    print line
                    print "-".center(80, '-')
                    biberrors += 1
    
    if biberrors > 0:
        print "{0} errors detected.  Received non-ASCII input".format(biberrors)
        #return an empty list so we don't process bad output
        return []
    return split_bibitems(bibliography, decomp)
    
def split_bibitems(bibliography, decomp):
    
    refs = []
    for filename, bib in bibliography.iteritems():
        split_ind = []
        for ind, item in enumerate(bib):
            if item.startswith(r"\bibitem"):
                split_ind.append(ind)
        
        
        for ref in partition(bib, split_ind):
            print ref
            if ref:
                refs.append(RefObj.RefObj(filename, refstr='\n'.join(ref), decomp=decomp))
    return refs

def partition(alist, indices):
    izip, chain = itertools.izip, itertools.chain
    pairs = izip(chain([0], indices), chain(indices, [None]))
    return (alist[i:j] for i, j in pairs)
     
def removeComments(rstr, join=True):
    if isinstance(rstr, str):
        rlines = rstr.splitlines()
    else:
        rlines = rstr
    newref = []
    for s in rlines:
        c = 0
        strlen = len(s)
        while (c < strlen):
            occ = s.find('%', c)
            if occ == -1:
                c = strlen
                break
            elif occ > 0 and s[occ-1] == '\\':
                c = occ + 1
            else:
                c = occ
                break
        newref.append(s[:c])
    return ''.join(newref) if join else newref

def matchBraces(string, openbrace='{', closebrace='}'):
    cnt = 0
    start = string.find(openbrace)
    for end, c in enumerate(string[start:], start):
        if c == openbrace:
            cnt += 1
        elif c == closebrace:
            cnt -= 1
            
        if cnt == 0:
            break
        
    return string[start+1:end]

def splitAuthor(authors, sep='and'):
    """Split string authors into a list of authors
    based on sep
    """
    
    return [k.strip() for k in authors.split(sep)]

def reformat(refstr, listed=False):
        r"""Reformat the reference.

        listed controls the return type.  If true, will return a list of the lines.
        If false, will return a string
        
        Changes self.refstr
        """
        
        formatted = ' '.join(refstr.split()).replace(r'\newblock', '\n\\newblock').splitlines()
        if listed:
            return formatted
        else:
            return '\n'.join(formatted)
