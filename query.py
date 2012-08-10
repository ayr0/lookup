'''
Created on Aug 1, 2012

@author: grout

Functions necessary for reference querying.  All queries pass through here
'''

from urllib import urlencode, quote
from urllib2 import urlopen, URLError
import util



def QueryDOI(ref):
    pass

def _get_pre_tag(data):
    '''Get the pre tag'''
    try:
        pretag = data[data.find("<pre>")+5:data.find("</pre>")]
        return pretag
    except:
        return None
        print "failed to find <pre></pre> tags", data

def link(data):
    """Parse link data
    
    return dictionary with MR"""
    
    ret = {}

    endtag = data.find(">") + 1
    ret['MRNUMBER'] = data[endtag:data.find("<", endtag)]
    return ret

def bibtex(data):
    """Parse bibtex data
    return dictionary of fields"""
    
    ret = {}
    match_data = [x.split('=') for x in data.splitlines()]
                          
    for x in match_data:
        try:
            entry = x[0].strip().upper()
            value = util.matchBraces(x[1], openbrace='{', closebrace='}')
            print entry == "AUTHOR"
            if entry == 'AUTHOR':
                ret[entry] = util.splitAuthor(value, 'and')
            else:
                ret[entry] = value
        except IndexError:
            pass
    
    return ret

def amsref(data):
    """Parse amsref data
    return dictionary of fields"""
    
    ret = {}
    match_data = [x.split('=') for x in data.splitlines()]
    
    for x in match_data:
        #make x[0] upper case
        #combine authors if possible
        try:
            entry = x[0].strip().upper()
            value = util.matchBraces(x[1], openbrace='{', closebrace='}')
            if entry == "AUTHOR":
                if entry in ret:
                    ret[entry].append(value)
                else:
                    ret[entry] = [value]
            elif entry == "REVIEW":
                ret["MRNUMBER"] = util.matchBraces(value, openbrace='{', closebrace='}')
            else:
                ret[entry] = value
        except IndexError:
            pass
    
    return ret          
    
def QueryMR(ref, overwrite, dataType='amsrefs', oldmr=""):
    """Fetch MR reference from ams.org and return
    
    You can set a preference:
    if overwrite evaluates True -> use AMS
    if overwrite evaluates False -> use oldmr if possible
    
    Datatype can be:
    link, amsrefs, bibtex
    """
    
    def cmpMR(mr1, mr2):
        """Return True if mr1 and mr2 are equal
        
        Expected MR types:
        MRxxxxxxx or xxxxxxx
        """
        if mr1[-7:] == mr2[-7:]:
            return True
        else:
            return False

    dataType = '&dataType=%s' % dataType #bibtex, amsrefs, link
    queryURL = 'http://www.ams.org/mathscinet-mref?ref='
    htmlquerystr = quote(ref.strip())
    testURL = "%s%s%s" % (queryURL, htmlquerystr, dataType)

    try:
        result = urlopen(testURL)
        #self.setMR(self._parse_return_link(result.read()))
        #print "Original MR: %s -> AMS MR: %s" % (self.ref_mr, self.ref_mr)
        n = "None".ljust(9)
        pretag = _get_pre_tag(result.read())
        amsmr = link(pretag)
        
        if oldmr and amsmr:
            if not cmpMR(oldmr, amsmr):
                mrmatch = "MR Mismatch"
                if overwrite:
                    msg = "Replacing with AMS"
                    return amsmr
                else:
                    msg = "Keeping Original"
            else:
                mrmatch = "MR Match"
                msg = "Keeping Original"
        elif amsmr and not oldmr:
            mrmatch = "!!MR FOUND!!"
            msg = "Inserting AMS"
            return amsmr
        else:
            mrmatch = "----------"
            
        msg = ""
        print "Original: %s\tAMS.org: %s\t%s\t%s" % \
            (oldmr if oldmr else n, 
                amsmr if amsmr else n, \
                mrmatch, msg)
    except URLError, error_msg:
        print "An error has occurred while opening url::",error_msg
        #print testURL
