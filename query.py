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
        pretag = data[data.find("<pre>")+5:data.find("</pre>")]
        return pretag
    except:
        return None
        print "failed to find <pre></pre> tags", data

def bibtex(data):
    """Parse bibtex data
    return dictionary of fields"""
    
    common = {'required': ['mrnumber'],
              'optional': ['doi']}
    article = {'required': ['author', 'title', 'journal', 'year'],
               'optional': ['volume', 'number', 'pages', 'month', 'note', 'key']}
    book = {'required': [('author', 'editor'), 'title', 'publisher', 'year'],
            'optional': [('volume', 'number'), 'series', 'address', 'edition', 'month', 'key', 'note']}
    incollection = {'required': ['author', 'title', 'booktitle', 'publisher', 'year'],
                    'optional': ['editor', ('volume', 'number'), 'series', 'type', 'chapter', 'pages', 'address', 'edition', 'month', 'key', 'note']}
    inproceedings = {'required': ['author', 'title', 'booktitle', 'year'],
                     'optional': ['editor', ('volume', 'number', )]}
    
    ret = {}
    match_data = [x.strip() for x in data.splitlines()]
    ret['type'] = match_data[0].split()[0][1:]
    for x in match_data[1:-1]:
        x = [k.strip() for k in x.split('=')]
        ret[x[0]] = x[1][1:-2]
    return ret
    
def amsref(data):
    """Parse amsref data
    return dictionary of fields"""
    
    pass
            
def QueryMR(ref, dataType='bibtex'):
    """Fetch MR reference from ams.org and return"""

    dataType = '&dataType=%s' % dataType #bibtex, amsrefs, tex, mathscinet
    queryURL = 'http://www.ams.org/mathscinet-mref?ref='
    htmlquerystr = quote(ref.strip())
    testURL = "%s%s%s" % (queryURL, htmlquerystr, dataType)

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
