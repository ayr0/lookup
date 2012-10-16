'''
Created on Aug 1, 2012

@author: grout

Functions necessary for reference querying.  All queries pass through here
'''

from urllib import urlencode, quote
from urllib2 import urlopen, URLError
from xml.etree import cElementTree as cET

import util
import parser

def QueryDOI(refs, email, batch):
    """Query DOI references.
    
    Expects a list of reference objects from which it will build a query
    """
    
    fields = {'author': ("AUTHOR",),
              'journal_title': ("JOURNAL",),
              'volume': ("VOLUME",),
              'first_page': ("PAGES",),
              'article_title': ("TITLE",),
              'proceedings_title': ("",),
              'volume_title': ("",),
              'year': ("YEAR", "DATE"),
              'isbn': ("ISBN",),
              'issn': ("ISSN",),
              'series_title': ("SERIES",),
              'unstructured_citation': ("",)}
    field_opts = {'author': {'search-all-authors':'false'},
                  'article_title': {'match':'fuzzy'}}
                  
              
              
    def queryElement(element):
        root_element = cET.Element("query", 
                            {'enable-multiple-hits':'multi_hit_per_rule',
                             'list-components':'false',
                             'expanded-results':'false',
                             'key': str(ref.ref_key)})

        #try to get the query from AMS
        _query = element.query
        
        #if element is a book
        if "ISBN" in _query:
            xml_element = cET.Element("ISBN")
        
        for f, v in fields.iteritems():
            tag = next((i for i, j in enumerate((vel in _query for vel in v)) if j), -1)
            
            if tag > -1:
                xml_element = cET.Element(f, field_opts.get(f, {}))
                print _query[v[tag]]
                xml_element.text = util.escape(_query[v[tag]])
                root_element.append(xml_element)
        return root_element
        

    #generate header
    header = cET.Element("query_batch", 
                         {'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 
                          'version':'2.0', 
                          'xmlns':'http://www.crossref.org/qschema/2.0', 
                          'xsi:schemaLocation':'http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd'})

    tree = cET.TreeBuilder()
    tree.start("head")
    tree.start("email_address")
    tree.data(email.strip())
    tree.end("email_address")
    tree.start("doi_batch_id")
    tree.data(batch.strip())
    tree.end("doi_batch_id")
    tree.end("head")

    header.append(tree.close())
    body = cET.Element("body")
    
    
    for ref in refs:
        body.append(queryElement(ref))
    header.append(body)

    return cET.tostring(header, "UTF-8")
    
    

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

def bibtex(data, first=True):
    """Parse bibtex data
    return dictionary of fields"""
    
    ret = {}
    s = parser.Parser(data)
    
    s.nextLiteral("@")
    s.nextWord()
    s.nextBrace()
    
    #start a sub parser
    print "sub parser"
    s.subParser()
    ret['mr'] = s.sub.nextWord(alphanum=True)
    s.sub.nextLiteral(',')
    
    while s.sub.pos < s.sub.end:
        key = s.sub.nextWord()
        s.sub.nextLiteral('=')
        val = s.sub.nextBrace()
        s.sub.nextLiteral(',')
        ret[key.lower()] = val
    
    return ret
    
    
    

def amsrefs(data, first=True):
    """Parse amsref data
    return dictionary of fields"""
    
    compound = ['book', 'conference', 'partial', 'reprint', 'translation']
    ret = {}
    s = parser.Parser(data)
    
    s.nextLiteral(r'\bib')
    ret["mr"] = s.nextBrace()
    s.nextBrace()
    s.nextBrace()
    
    s.subParser()
    while s.sub.pos < s.sub.end:
        key = s.sub.nextWord()
        s.sub.nextLiteral('=')
        val = s.sub.nextBrace()
        
        #if we have a book key
        if key in compound:
            subdict = {}
            s.sub.subParser()
            p = s.sub.sub
            while s.sub.sub.pos < s.sub.sub.end:
                subkey = p.nextWord()
                p.nextLiteral('=')
                subval = p.nextBrace()
                p.nextLiteral(',')
                subdict[subkey] = subval
            val = subdict
            
        s.sub.nextLiteral(',')
        ret[key] = val
        
    return ret
    
def QueryMR(ref, dataType='bibtex'):
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
        print "returning ",amsmr
        return pretag
    except URLError, error_msg:
        print "An error has occurred while opening url::", error_msg, testURL
        return
    except KeyError:
        print "Unknown datatype! please use 'amsrefs', 'bibtex', or 'link'"
        return
        #print testURL
    except:
        print "Unknown Error"
        return