__author__ = 'grout'

import hashlib
import logging

import util
import query

class RefObj(object):
    def __init__(self, filename, refstr="", **attrs):
    
        self.attrs = attrs
        self.ref_file = filename
        refstrlist = util.reformat(refstr, listed=True)
        
        doi_data = self._removeDOI(refstrlist[0])
        mr_data = self._removeMR(doi_data[0])
        refstrlist[0] = mr_data[0]
        self.ref_str = '\n'.join(refstrlist)
        
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

        if mode == 1:
            logging.info("Mode = 1: returning MR={}\tDOI={}".format(self.ref_mr, self.ref_doi))
            return
        else:
            self.query = query.QueryMR(self.ref_str, dataType=dataType)
            logging.debug(self.query)
            logging.debug(self.ref_str)
            
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
            