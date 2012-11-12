__author__ = 'grout'

import hashlib
import logging

import util
import query

class RefObj(object):
    def __init__(self, filename, refstr="", decomp=False, **attrs):
    
        self.attrs = attrs
        self.ref_file = filename
        refstr = util.removeComments(refstr)
        
        doi_data = self._removeDOI(refstr)
        mr_data = self._removeMR(doi_data[0])
        self.ref_str = mr_data[0]
        
        self.ref_mr = mr_data[1]
        self.ref_doi = doi_data[1]
        self.ref_key = hashlib.sha256(''.join(self.ref_str.split())).hexdigest()
        
        #print "Created reference (MR: %s\tDOI: %s)" % (self.ref_mr, self.ref_doi)
        
    def _existDOI(self, bibstr):
        '''If DOI exists in bibstr, return True.  Otherwise, return False'''
        
        doistr = util.reformat(bibstr, listed=True)[0]
        doistr = self._removeDOI(doistr)[1]
        if doistr:
            #print "Using existing DOI number", doistr
            self.setDOI(doistr)

        return doistr

    def _existMR(self, bibstr):
        '''Return True if MR reference is present'''

        #format the reference
        mrstr = util.reformat(bibstr, listed=True)[0]
        mrstr = self._removeMR(mrstr)[1]
        if mrstr:
            #print "Using existing MR number",mrstr
            self.setMR(mrstr)

        return mrstr

    def _removeDOI(self, bibstr):
        '''
        Find and remove doi reference from bibstr.

        This is because ams.org doesn't like doi in query references

        Returns bibstr with doi removed and doistr
        '''

        #We need to strip the doi reference before query
        #DOI references always begin with '10.'

        doi1 = bibstr.find("[10.")
        doi2 = bibstr.find("[doi:10.")
        doiend = bibstr.find("]")+1
        doistr = ""

        if doi1 >= 0 and doiend > doi1:
            doistr = bibstr[doi1:doiend]
            bibstr = bibstr.replace(bibstr[doi1:doiend], "")
        elif doi2 >= 0 and doiend > doi2:
            doistr = bibstr[doi2:doiend]
            bibstr = bibstr.replace(bibstr[doi2:doiend], "")

        return bibstr,doistr[1:-1]

    def _removeMR(self, bibstr):
        '''Return a copy of bibstr with MR reference removed and returned separately

        This function is used to avoid multiple MR references in the output.'''

        mrstart1 = bibstr.find("(")
        mrstart2 = bibstr.find("(MR")
        mrend = bibstr.find(")")+1
        mrstr = ""

        if mrstart1 >= 0 and mrend > mrstart1 and mrend-mrstart1==8:
            mrstr = bibstr[mrstart1:mrend]
            bibstr = bibstr.replace(bibstr[mrstart1:mrend], "")
        elif mrstart2 >= 0  and mrend > mrstart2:
            mrstr = bibstr[mrstart2:mrend]
            bibstr = bibstr.replace(bibstr[mrstart2:mrend], "")

        return bibstr, mrstr[1:-1]


    
    def _dcomp(self):
        """Decompose  reference if needed into a dictionary containing:
        {Author:*, Title:*, Journal:*, IssueN:*, FirstPage:,}
        """

        def tsplit(s, sep):
            stack = [s]
            for char in sep:
                pieces = []
                for substr in stack:
                    pieces.extend(substr.split(char))
                    stack = pieces
            return stack

        def getNums(s):
            """Return a list of numbers found in the string"""

            nums = []
            s = s.center(len(s)+2)
            bs, es = None, None
            for i,c in enumerate(s):
                if c.isdigit():
                    if bs is None:
                        bs=es=i
                    else:
                        es = i+1 if i+1 != len(s) else -1
                    if not s[es].isdigit():
                        nums.append(int(s[bs:es]))
                else:
                    bs, es = None, None
            return nums

        decomp = {}
        reflines = [l.strip() for l in self.ref_str.split(r'\newblock')]
        #reflines = self.ref_str.splitlines()
        #reflines = [line.strip() for line in reflines]

        #remove any comment lines
        #reflines = [l[:l.find("%")] for l in reflines]
        #remove empty lines
        reflines = [l for l in reflines if l]

        #Author(s)
        #author = reflines[1].replace(r'\newblock', '').strip()
        decomp['author'] = tsplit(reflines[1], (',', ' and '))#[:-1]

        #Title
        title = reflines[2]#.replace(r'\newblock', '').strip()

        bslice = 0
        eslice = 0
        #is there an \emph{
        if title.startswith(r'\emph{'):
            bslice = 6
            eslice = title.rfind('}')
        elif title.startswith(r'``'):
            bslice = 2
            eslice = title.rfind("''")
            e2slice = title.rfind('"')
            eslice = eslice if eslice >= e2slice else e2slice
            decomp['type'] = 'volume'
        decomp['article_title'] = title[bslice:eslice]

        #Third newblock
        other = reflines[3]#.replace(r'\newblock', '')
        other = other.split(',')
        decomp['title'] = other[0].strip()

        if other[0].lower().find('Proc.') > 0:
            decomp['type'] = 'proceedings'
        else:
            decomp['type'] = 'journal'


        if other[1].find(r'\textbf') or other[1].find(r'{\bf'):
            vol, year = getNums(other[1])
            decomp['volume']=vol
            decomp['year']=year


        try:
            fp, lp = getNums(other[-1])
            decomp['first_page']=fp
            decomp['last_page']=lp
        except ValueError:
            pass

        return decomp

    def addRefs(self, mr=True, doi=True):

        
        lines = self.ref_str.splitlines()
        bibline = lines[0]
        #try to figure out the end of \bibitem string
        #\bibitem[maybe]{required}
        #find the places in the string
        s = bibline.find(r'\bibitem')

        #find the last bracket
        (superb, subb) = [0, 0]
        for i in range(len(bibline)):
        #take care of square brackets
            if bibline[i] == "[":
                superb += 1
            elif bibline[i] == "]":
                superb -= 1

            if superb is 0:
                if bibline[i] == "{":
                    superb += 1
            elif superb > 0:
                if subb is 0 and bibline[i] == "}":
                    superb = i + 1
                else:
                    if bibline[i] == "{":
                        subb += 1
                    elif bibline[i] == "}":
                        subb -= 1

        if not self.ref_mr:
            if not self.ref_doi:
                lines[0] = "{0} \n {1}".format(bibline[s:superb], bibline[superb:])
            else:
                #no mr_str, but exists doi_str
                lines[0] = "{0} [{1}] \n {2}".format(bibline[s:superb], self.ref_doi, bibline[superb:])
        else:
            #mr_str exists, doi_str is null
            if not self.ref_doi:
                lines[0] = "{0} ({1}) \n {2}".format(bibline[s:superb], self.ref_mr, bibline[superb:])
            else:
                #mr_str and doi_str
                lines[0] = "{0} ({1}) [{2}] \n {3}".format(bibline[s:superb], self.ref_mr, self.ref_doi, bibline[superb:])

        #print "bibline: %s" % bibline
        #print "MR: %s \t DOI: %s" % (self.ref_mr, self.ref_doi)
        #print "setting %s" % lines[0]
        lines[-1] = lines[-1] + "\n\n"
        return ''.join(lines)

    def fetchMR(self, mode=2, dataType="amsrefs"):
        """Fetch MR reference from ams.org
        
        modes:
        0: always use AMS values
        1: always use existing values
        2: use AMS only when no existing value else existing value
        """
        #Use query module
        self.query = query.QueryMR(self.ref_str, dataType=dataType)
        logging.debug(self.query)
        logging.debug(self.ref_str)
        if mode == 1:
            logging.info("Mode = 1: returning MR={}\tDOI={}".format(self.ref_mr, self.ref_doi))
            return
        else:
            try:
                amsmr = self.query.get("mr", "")
                doicref = self.query.get("doi", "")
                
                if mode == 0:
                    logging.info("Mode = 0: setting MR={}\tDOI={}".format(amsmr, doicref))
                    self.setMR(amsmr)
                    self.setDOI(doicref)
                elif mode == 2 and not self.ref_mr:
                    logging.info("Mode = 2: existing MR: {}\tsetting MR={}".format(self.ref_mr, amsmr))
                    self.setMR(amsmr)
                
                if mode == 2 and not self.ref_doi:
                    logging.info("Mode = 2: existing DOI: {}\tsetting DOI={}".format(self.ref_doi, doicref))
                    self.setDOI(doicref)
            except AttributeError:
                pass
            except KeyError:
                pass

    def setDOI(self, doi):
        """Setter for DOI reference number"""
        if isinstance(doi, str):
            self.ref_doi = doi.strip()

    def setMR(self, mr):
        """Setter for MR reference number"""
        if isinstance(mr, str):
            if mr.startswith("MR"):
                self.ref_mr = mr.strip()
            