__author__ = 'grout'

import hashlib
import re
import util
from urllib import urlencode, quote
from urllib2 import urlopen, URLError
from xml.dom import minidom
import logging

class RefObj(object):
    def __init__(self, filename, refstr = "", decomp=True, **attrs):
    
        self.attrs = attrs
        self.ref_file = filename
        refstr = self._rmComments(refstr)
        
        mr_data = self._removeMR(refstr)
        doi_data = self._removeDOI(mr_data[0])
        self.ref_str = doi_data[0]
        
        self.ref_mr = mr_data[1]
        self.ref_doi = doi_data[1]
        self.ref_key = hashlib.sha256(''.join(self.ref_str.split())).hexdigest()
        
        self.dataType = '&dataType=link' #bibtex, amsrefs, tex, mathscinet
        self.queryURL = 'http://www.ams.org/mathscinet-mref?ref='
        
        print "Created reference (MR: %s\tDOI: %s)" % (self.ref_mr, self.ref_doi)

        self._reformat(listed=False)
        if decomp:
            try:
                self.decomp = self._dcomp()
                print "Decomposed reference"
            except:
                print "Decomposition failed!".center(80, '-')

    def _rmComments(self, rstr):
        '''remove any commented lines in the reference'''
        return util.removeComments(rstr)
        
    def _existDOI(self, bibstr):
        '''If DOI exists in bibstr, return True.  Otherwise, return False'''
        
        doistr = self._reformat(ref=bibstr, listed=True)[0]
        doistr = self._removeDOI(doistr)[1]
        if doistr:
            #print "Using existing DOI number", doistr
            self.setDOI(doistr)

        return doistr

    def _existMR(self, bibstr):
        '''Return True if MR reference is present'''

        #format the reference
        mrstr = self._reformat(ref=bibstr, listed=True)[0]
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


    def _reformat(self, ref=None, listed=False):
        r"""Reformat the reference.

        listed controls the return type.  If true, will return a list of the lines.
        If false, will return a string
        
        Changes self.refstr
        """
        
        if ref is None:
            ref = self.ref_str
            
        formatted = ' '.join(self.ref_str.split()).replace(r'\newblock', '\n\\newblock').splitlines()
        if listed:
            return formatted
        else:
            return '\n'.join(formatted)

    def _parse_return_link(self, data):
        '''Parse returned link to get MR number'''

        try:
            prestr = self._get_pre_tag(data)
            return "MR"+re.search(r'\?mr=(\d{7})\"', str(prestr), re.S).groups()[0]
        except:
            return None
            print "failed in parse_return_link"

    def _get_pre_tag(self, data):
        '''Get the pre tag'''
        try:
            pretag = re.search(r'<pre>(.+)</pre>', str(data), re.S).groups()[0]
            return pretag
        except:
            return None
            print "failed to find <pre></pre> tags", data

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

        #block = self.ref_str

        #if not self.ref_doi:
        #    refless_block = self._removeDOI(block)[0]
        #else:
        #    refless_block = block

        #refless_block = self._removeMR(refless_block)[0]

        #lines = refless_block.splitlines()
        #bibline = lines[0]
        
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
                lines[0] = "%s \n %s" % (bibline[s:superb], bibline[superb:])
            else:
                #no mr_str, but exists doi_str
                lines[0] = "%s [%s] \n %s" % (bibline[s:superb], self.ref_doi, bibline[superb:])
        else:
            #mr_str exists, doi_str is null
            if not self.ref_doi:
                lines[0] = "%s (%s) \n %s" % (bibline[s:superb], self.ref_mr, bibline[superb:])
            else:
                #mr_str and doi_str
                lines[0] = "%s (%s) [%s] \n %s" % (bibline[s:superb], self.ref_mr, self.ref_doi, bibline[superb:])

        #print "bibline: %s" % bibline
        #print "MR: %s \t DOI: %s" % (self.ref_mr, self.ref_doi)
        #print "setting %s" % lines[0]
        lines[-1] = lines[-1] + "\n\n"
        return ''.join(lines)

    def fetchMR(self, overwrite=False):
        """Fetch MR reference from ams.org"""

        #if not overwrite:
            ##check for existing MR
            #if self.ref_mr:
                ##make a copy of the mr reference
                #self.old_mr = self.ref_mr

        htmlquerystr = quote(self.ref_str.strip())
        testURL = "%s%s%s" % (self.queryURL, htmlquerystr, self.dataType)

        try:
            result = urlopen(testURL)
            #self.setMR(self._parse_return_link(result.read()))
            #print "Original MR: %s -> AMS MR: %s" % (self.ref_mr, self.ref_mr)
            n = "None".ljust(9)
            amsmr = self._parse_return_link(result.read())
            oldmr = self.ref_mr
            if self.ref_mr and amsmr:
                if not self.cmpMR(self.ref_mr, amsmr):
                    mrmatch = "MR Mismatch"
                    if overwrite is True:
                        msg = "Replacing with AMS"
                        self.setMR(amsmr)
                    else:
                        msg = "Keeping Original"
                else:
                    mrmatch = "MR Match"
                    msg = "Keeping Original"
            elif amsmr and not self.ref_mr:
                mrmatch = "!!MR FOUND!!"
                msg = "Inserting AMS"
                self.setMR(amsmr)
            else:
                mrmatch = "----------"
                
            msg = ""
            print "Original: %s\tAMS.org: %s\t%s\t%s" % \
                (oldmr if oldmr else n, 
                    amsmr if amsmr else n, \
                    mrmatch, msg)
        except URLError, error_msg:
            print "An error has occured while opening url::",error_msg
            #print testURL

    def fetchDOI(self, user, passwd, overwrite=False):
        """Fetch DOI reference from crossref.org
        This will ONLY work for decomposed references.
        This requires a crossref account"""

        
        #account = "%s:%s" % (user, passwd)


        #url = r"http://www.crossref.org/openurl?pid=%s&" % account.strip()
        url = r"http://doi.crossref.org/servlet/query?usr={0}&pwd={1}".format(user, passwd)
        unixref = r"&redirect=false&multihit=false&format=unixref&qdata="
        #opts = ""

    #if we have decomposed the reference, we should use the elements
        if hasattr(self, 'decomp'):
            authorlast = self.decomp['author'][0].split()[-1] \
                            if self.decomp.has_key('author') else ""
            journaltitle = self.decomp['title'] \
                            if self.decomp.has_key('title') else ""
            firstpage = self.decomp['first_page'] \
                            if self.decomp.has_key('first_page') else ""
            volume = self.decomp['volume'] \
                            if self.decomp.has_key('volume') else ""
            date = self.decomp['year'] \
                            if self.decomp.has_key('year') else ""

            opts = urlencode({'aulast':authorlast, 
                                'title':journaltitle,
                                'spage':firstpage,
                                'volume':volume,
                                'date':date})
        
        try:
            result = urlopen("%s%s%s" % (url, opts, unixref)).read()
            doc = minidom.parseString(result)
            dois = doc.getElementsByTagName('doi')
            print dois
            dois = [doi.childNodes[0].nodeValue for doi in dois]
        except:
            pass

        print "%s%s%s" % (url, opts, unixref)

    def setDOI(self, doi):
        """Setter for DOI reference number"""
        if isinstance(doi, str):
            self.ref_doi = doi

    def setMR(self, mr):
        """Setter for MR reference number"""
        if isinstance(mr, str):
            self.ref_mr = mr
    
    def cmpMR(self, mr1, mr2):
        """Return True if mr1 and mr2 are equalj
        
        Expected MR types:
        MRxxxxxxx or xxxxxxx
        """
        if mr1[-7:] == mr2[-7:]:
            return True
        else:
            return False