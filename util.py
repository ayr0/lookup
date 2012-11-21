#Utility functions

import os
import RefObj
import fileinput
import itertools
import ConfigParser
import string

subs = {r'\&': '&',
        r"\'": '',
        r'\"': '',
        r'\newblock': '',
        r'\textbf': '', r'\bf': '',
        r'{': '', r'}': '',
        r'\emph': '',
        r'\mathbb': '',
        r'$': '',
        r'~': ' '}

def getsubst():
    
    f = ConfigParser.SafeConfigParser()
    f.read("crossref.cfg")
    
    global subs
    
    try:
        for val, sub in f.items('detex'):
            subs[val] = sub
    except ConfigParser.NoSectionError:
        return None

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
            if not line.isspace() and not line.startswith('%'):
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
            
def splitAuthor(authors, sep='and', first=True):
    """Split string authors into a list of authors
    based on sep and return the first author only if first is True
    """
    
    tmp = [k.strip() for k in authors.split(sep)]
    if first is True:
        return tmp[0].split(',')[0].strip()
    else:
        return tmp

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

def firstpage(pages):
    """Extract first page number from the PAGES field"""
    return pages[:pages.find('--')]

def escape(text):
    """Escape illegal XML characters

    & -> &amp;
    < -> &lt;
    > -> &gt;
    """
    if isinstance(text, list):
        for i, t in enumerate(text):
            t = t.replace(r'&', r'&amp;')
            t = t.replace(r'<', r'&lt;')
            t = t.replace(r'>', r'&gt;')
            text[i] = t
    else:
        text = text.replace(r'&', r'&amp;')
        text = text.replace(r'<', r'&lt;')
        text = text.replace(r'>', r'&gt;')
    return text

def detex(tex):
    """Replace the bibtex item.  Assumes no reference numbers and a single reference"""
    
    tex = '\n'.join(reformat(tex, listed=True)[1:])
    global subs
    
    for old, new in subs.iteritems():
        tex = tex.replace(old, new)
    
    return tex.strip()

def findKey(key, refs):
    for i, r in enumerate(refs):
        if key == r.ref_key:
            return i
            
    