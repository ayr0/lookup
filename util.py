#Utility functions

import re
import os
import RefObj
import fileinput
import itertools
import logging

bib_regex_str = r'''
    (?!\\begin{thebibliography})        #find '\begin{thebibliography}' but don't start matching till AFTER
    (\\bibitem.+?)                      #start match at each '\bibitem' phrase
    (?=\\bibitem                        #Match until next '\bibitem' is found
    |                                   # OR
    \\end{thebibliography}              #until '\end{thebibliography}' is found
    |                                   # OR
    \%)                                  #until a comment
    '''

bib_regex = re.compile(bib_regex_str, re.S|re.VERBOSE)

def load_bib_lines(filenames, decomp=True):
    """Load *.tex files and read them line by line.
    This method only loads the bibliography section and checks for ascii"""
    
    bibliography = {}
    bibsection = 0
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
                except UnicodeEncodeError:
                    print "Special Character on line {0} in file {0}".format(fileinput.filelineno(), fileinput.filename())
                    print line
                    print "-".center(80, '-')
                bibitems.append(line.strip())
    
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
 
def load_bib_blocks(filename, decomp=True):
    """Load *.tex files and extract the bibliography section with references"""
    refs = []

    try:
        #file exists, now try to open
        with open(filename, 'r') as tex_file:
            texlines = tex_file.readlines()
        
    except:
        print "This doesn't appear to be a file."
        
    #texstr = removeComments(texlines)
    bib_blocks = re.findall(bib_regex, ''.join(texlines))


    for i in xrange(len(bib_blocks)):
        #check for illegal characters
        #bib_blocks[i] = bib_blocks[i].replace(r'&', r'&amp;')
        ref = RefObj.RefObj(os.path.abspath(filename), bib_blocks[i], decomp=decomp)
        refs.append(ref)
    return refs
    
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
            #print "occ: ", occ
            #print "string slice: ", rstr[occ-10:occ+10]
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