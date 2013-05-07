#Utility functions

import os
import RefObj
import fileinput
import itertools
import ConfigParser

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
    """Read character substitutions from crossref.cfg and store them in a global dictionary"""
    
    f = ConfigParser.SafeConfigParser()
    f.read("crossref.cfg")
    
    global subs
    
    try:
        for val, sub in f.items('detex'):
            subs[val] = sub
    except ConfigParser.NoSectionError:
        return None

def expandFilenames(filenames):
    """Expand relative filenames to absolute paths"""
    
    abs_filenames = []
    for f in filenames:
        abs_filenames.append(os.path.abspath(f))
    
    return abs_filenames

def load_bib_lines(filenames):
    """Load *.tex files and read them line by line.
    This method only loads the bibliography section and checks for ascii"""
    
    bibliography = {}
    bibsection = 0
    biberrors = 0
    filenames = expandFilenames(filenames)
    for line in fileinput.input(filenames, mode='rU'):
        #iterate until we get to a bibitem section
        line = line.strip()
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
                    candline = removeComment(line)
                    if candline:
                        bibitems.append(candline)
                except UnicodeDecodeError:
                    print "Special Character on line {0} in file {1}".format(fileinput.filelineno(), fileinput.filename())
                    print line
                    print "-".center(80, '-')
                    biberrors += 1
    
    if biberrors > 0:
        print "{0} errors detected.  Received non-ASCII input".format(biberrors)
        #return an empty list so we don't process bad output
        return []
    
    return split_bibitems(bibliography)
    
def split_bibitems(bibliography):
    """Split the bibliography into bibitem blocks"""
    
    refs = []
    for filename, bib in bibliography.iteritems():
        split_ind = []
        for ind, item in enumerate(bib):
            if item.startswith(r"\bibitem"):
                split_ind.append(ind)
                
        for ref in partition(bib, split_ind):
            if ref:
                refs.append(RefObj.RefObj(filename, refstr='\n'.join(ref)))
    return refs

def partition(alist, indices):
    """Recipe from itertools"""
    izip, chain = itertools.izip, itertools.chain
    pairs = izip(chain([0], indices), chain(indices, [None]))
    return (alist[i:j] for i, j in pairs)
     
def removeComment(line):
    """Given a line of text, remove everything after the first non-escaped %"""
    ind = line.find('%')
    while True:
        if ind < 0:
            return line
        elif (ind > 0 and line[ind-1] != '\\') or ind == 0:
            break
        else:
            ind = line.find('%', ind+1)
    return line[:ind]
        
def splitAuthor(authors, sep='and', first=True):
    """Split string authors into a list of authors
    based on sep and return the first author only if first is True
    """
    tmp = [k.strip() for k in authors.split(sep)]
    if first:
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


def escape(text):
    """Escape illegal XML characters

    & -> &amp;
    < -> &lt;
    > -> &gt;
    """
    if isinstance(text, list):
        for i, t in enumerate(text):
            t = t.replace(r'\&', r'&amp;')
            t = t.replace(r'<', r'&lt;')
            t = t.replace(r'>', r'&gt;')
            text[i] = t
    else:
        text = text.replace(r'\&', r'&amp;')
        text = text.replace(r'<', r'&lt;')
        text = text.replace(r'>', r'&gt;')
    return text

def unescape(text):
    """Unescape illegal XML characters

    &amp -> &;
    &lt -> <;
    &gt -> >;
    """
    if isinstance(text, list):
        for i, t in enumerate(text):
            t = t.replace(r'&amp;', r'\&')
            t = t.replace(r'&lt;', r'<')
            t = t.replace(r'&gt;', r'>')
            text[i] = t
    else:
        text = text.replace(r'&amp;', r'\&')
        text = text.replace(r'&lt;', r'<')
        text = text.replace(r'&gt;', r'>')
    return text
    

def detex(tex):
    """Replace the bibtex item.  Assumes no reference numbers and a single reference"""
    
    #tex = '\n'.join(reformat(tex, listed=True)[1:])
    global subs
    
    for old, new in subs.iteritems():
        tex = tex.replace(old, new)
    
    return tex.strip()

def escape_replace(s, old, new, escape='\\'):
    """A character escape aware string replace function
    
    s = string to perform replacement with
    old = substring to replace
    new = string to replace old
    escape = the escape character to be aware of
    """
    newstr = []
    if len(old) == 0:
        return

    for i, c in enumerate(s):
        if old[0] == c and s[i-1] != escape:
            newstr.extend(new)
        else:
            newstr.append(c)
    return ''.join(newstr)
            
def sanitizeXML(filename):
    """Crossref often doesn't properly escape ampersands in its XML returns
    
    Before  parsing the xml, we need to escape these ampersands properly
    """
    #we have to remove all illegal characters from crossref xml
    full_path = os.path.abspath(filename)
    path, filename = os.path.split(full_path)
    with open(full_path, 'r') as in_file:
        with open(os.path.join(path,"tmp"+filename), 'w') as out_file:
            for line in in_file:
                out_file.write(line.replace(r'&', r'&amp;'))
    os.remove(full_path)
    os.rename(os.path.join(path, "tmp"+filename), os.path.join(path, filename))
    
    return full_path
    
    