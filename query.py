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
    pre_start = data.find("<pre>") + 5
    pre_end = data.find("</pre>")
    if pre_end != -1:
        pretag = data[pre_start:pre_end]
        return pretag
    else:
        return ""
    
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

def amsrefs(data):
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
    
def QueryMR(ref, dataType='amsrefs'):
    """Fetch MR reference from ams.org and return
    
    You can set a preference:
    if overwrite evaluates True -> use AMS
    if overwrite evaluates False -> use oldmr if possible
    
    Datatype can be:
    link, amsrefs, bibtex
    """
    
    handler = {'link': link,
               'amsrefs': amsrefs,
               'bibtex': bibtex}
    
    def cmpMR(mr1, mr2):
        """Return True if mr1 and mr2 are equal
        
        Expected MR types:
        MRxxxxxxx or xxxxxxx
        """
        if mr1[-7:] == mr2[-7:]:
            return True
        else:
            return False

    #queryURL = 'http://www.ams.org/mathscinet-mref?ref='
    testURL = r"http://www.ams.org/mathscinet-mref?ref={0}&dataType={1}".format(quote(ref.strip()), 
                                                                                dataType)

    try:
        result = urlopen(testURL)
        #self.setMR(self._parse_return_link(result.read()))
        #print "Original MR: %s -> AMS MR: %s" % (self.ref_mr, self.ref_mr)
        pretag = _get_pre_tag(result.read())
        amsmr = handler[dataType](pretag)
        
        return 0, amsmr
    except URLError, error_msg:
        print "An error has occurred while opening url::", error_msg, testURL
        return 2, None
    except KeyError:
        print "Unknown datatype! please use 'amsrefs', 'bibtex', or 'link'"
        return 3, None
        #print testURL
    except:
        return 1, None
