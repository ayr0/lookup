'''
Created on Aug 1, 2012

@author: grout

Functions necessary for reference querying.  All queries pass through here

This code uses the Requests library to POST xml files to Crossref.
--------------Requests License----------------------------
Copyright (c) 2012 Kenneth Reitz.

Permission to use, copy, modify, and/or distribute this software for any 
purpose with or without fee is hereby granted, provided that the above 
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OF PERFORMANCE OF THIS SOFTWARE.
------------------------------------------------------------
'''

from urllib import quote
from urllib2 import urlopen, URLError
from xml.etree import cElementTree as cET
from copy import copy
import logging
import util
import proc
import rparser

_requests = False
try:
    import requests
    _requests = True
except ImportError:
    pass

class NoContentError(Exception):
    pass

class PostError(Exception):
    pass

def QueryDOI(refs, batch, cross_opts):
    """Query DOI references.
    
    Expects a list of reference objects from which it will build a query
    batch = string identifying the batch
    cross_opts = a dictionary of options for crossref (from crossref.cfg
    """
    
    fields = {'author': ("author",),
              'journal_title': ("journal",),
              'volume': ("volume",),
              'first_page': ("pages",),
              'article_title': ("title",),
              'proceedings_title': ("",),
              'volume_title': ("",),
              'year': ("year", "date"),
              'isbn': ("isbn",),
              'issn': ("issn",),
              'series_title': ("series",),
              'unstructured_citation': ("",)}
    
    field_processors = {'first_page': proc.firstpage,
                        'issn': proc.issn,
                        'author': proc.author}
    
    field_opts = {'author': {'search-all-authors':'true'},
                  'article_title': {'match':'fuzzy'}}
                  
    root_element = lambda key: cET.Element("query", 
                                           {'enable-multiple-hits':'false',
                                            'secondary-query':'author-title',
                                            'list-components':'false',
                                            'expanded-results':'false',
                                            'key': str(key)})
    
    header = cET.Element("query_batch", 
                         {'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 
                          'version':'2.0', 
                          'xmlns':'http://www.crossref.org/qschema/2.0', 
                          'xsi:schemaLocation':'http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd'})

              
    def queryElement(element):
        """Build a single query element"""
        
        #try to get the query from AMS
        _query = element.query
        
        
        root = root_element(element.ref_key)
        for f, v in fields.iteritems():
            tag = next((i for i, j in enumerate((vel in _query for vel in v)) if j), -1)
            
            if tag > -1:
                xml_element = cET.Element(f, field_opts.get(f, {}))
                qtext = util.escape(_query[v[tag]])
                if f in field_processors:
                    xml_element.text = field_processors[f](qtext)
                else:
                    xml_element.text = qtext
                root.append(xml_element)
        logging.debug(cET.tostring(root, "UTF-8"))
        return root
         
    #generate a header    
    tree = cET.TreeBuilder()
    tree.start("head")
    tree.start("email_address")
    tree.data(cross_opts['email'].strip())
    tree.end("email_address")
    tree.start("doi_batch_id")
    tree.data(batch.strip())
    tree.end("doi_batch_id")
    tree.end("head")

    header.append(tree.close())
    
    if cross_opts.get('query_all', 'False') == 'True':
        query_refs = refs
    else:
        query_refs = [r for r in refs if r.ref_doi]
        
    num_query = len(query_refs)       
    per_file = int(cross_opts['queries_per_file'])
    query_refs = [query_refs[i:i+per_file] for i in xrange(0, len(query_refs), per_file)]
    file_list = []
    for num, chunk in enumerate(query_refs):
        h = copy(header)
        body = cET.Element("body")
        for ref in chunk:
            if ref.query != {}:
                body.append(queryElement(ref))
            else:
                #we need to add an unstructured_citation
                #but first we try an author-title search
                try:
                    #parse ref for author and title
                    r = util.reformat(ref.ref_str, listed=True)
                    
                    #the len(r'\newblock') = 9, so slice it off
                    aut = util.splitAuthor(r[1][9:].strip(), first=True)
                    ref.query['author'] = aut
                    t = util.detex(r[2][9:]).strip()
                    ref.query['title'] = t
                    
                    body.append(queryElement(ref))
                except:
                    qElem = root_element(ref.ref_key)
                    unstruct_cit = cET.Element("unstructured_citation")
                    unstruct_cit.text = util.detex(ref.ref_str)
                    qElem.append(unstruct_cit)
                    body.append(qElem)
                    
        
        h.append(body)
        
        file_list.append("{0}_{1}.xml".format(batch, num))
        with open(file_list[-1], 'w') as outFile:
            print "Writing File ", num
            outFile.write(cET.tostring(h, "UTF-8"))
    print "Queried {}/{} references".format(num_query, len(refs))
    return file_list
            
def post(post_files, login, passwd):
    """Send files via http to crossref.  Used to post xml files
    
    post_files = a list of file to send to crossref
    login = the account login
    passwd = the account passwd
    """
    
    if _requests:
        crossref_url = 'http://doi.crossref.org/servlet/deposit?login_id={0}&login_passwd={1}'.format(login, passwd)
        dat = {'area':'live', 'operation':'doQueryUpload'}
        for f in post_files:
            r = requests.post(crossref_url, data=dat, files={f:open(f, 'r')})
            if r.status_code == 200:
                print "Uploaded ", f
            else:
                print "{} did not upload correctly. {}".format(f, r.reason)
    else:
        raise PostError("requests library not found")
    
def _get_pre_tag(data):
    '''Get the pre tag'''
    pre_start = data.find("<pre>") + 5
    pre_end = data.find("</pre>")
    if pre_end != -1:
        pretag = data[pre_start:pre_end]
        return pretag.replace('&lt;', '<').replace('&gt;', '>')
    else:
        raise NoContentError
    
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
    s = rparser.Parser(data)
    
    s.nextLiteral("@")
    s.nextWord()
    s.nextBrace()
    
    #start a sub parser
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
    s = rparser.Parser(data)
    
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
        pretag = _get_pre_tag(result.read())
        amsmr = handler[dataType](pretag)
        return amsmr
    except URLError, error_msg:
        print "An error has occurred while opening url::", error_msg, testURL
        return {}
    except KeyError:
        print "Unknown datatype! please use 'amsrefs', 'bibtex', or 'link'"
        return {}
    except NoContentError:
        return {}
    
def fetchMR(ref, mode=2, dataType="amsrefs"):
        """Fetch MR reference from ams.org
        
        modes:
        0: always use AMS values
        1: always use existing values
        2: use AMS only when no existing value else existing value
        
        dataType = "amsrefs" or "bibtex" or "link"
        """

        if mode == 1:
            logging.info("Mode = 1: returning MR={}\tDOI={}".format(ref.ref_mr, ref.ref_doi))
            return
        else:
            ref.query = QueryMR(ref.ref_str, dataType=dataType)
            logging.debug(ref.query)
            logging.debug(ref.ref_str)
            
            try:
                amsmr = ref.query.get("mr", "")
                doicref = ref.query.get("doi", "")
                
                if mode == 0:
                    logging.info("Mode = 0: setting MR={}\tDOI={}".format(amsmr, doicref))
                    ref.setMR(amsmr)
                    ref.setDOI(doicref)
                elif mode == 2 and not ref.ref_mr:
                    logging.info("Mode = 2: existing MR: {}\tsetting MR={}".format(ref.ref_mr, amsmr))
                    ref.setMR(amsmr)
                
                if mode == 2 and not ref.ref_doi:
                    logging.info("Mode = 2: existing DOI: {}\tsetting DOI={}".format(ref.ref_doi, doicref))
                    ref.setDOI(doicref)
            except AttributeError:
                pass
            except KeyError:
                pass