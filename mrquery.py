__author__ = 'grout'

import os
import cPickle
from xml.dom import minidom
import util
import query
import logging
import ConfigParser



def generateFileList(refs):
    """Generate a list of files that had the original references.

    The filename that contains a given reference is stored in the reference object.
    If we did a DOI query, there is no need to give files to mrquery"""
    files = set()
    for ref in refs:
        files.add(ref.ref_file)
    return list(files)

def writeMRefFile(references):
    """Write the references to another file."""

    files = generateFileList(references)
    for f in files:
        fname = "{}_refs.tex".format(os.path.splitext(f)[0])
        with open(fname, "w") as ofile:
            for ref in references:
                if ref.ref_file == f:
                    ofile.write('%s\n\n' % util.reformat(ref.addRefs()))
        print "Wrote to ", fname

def loadDoi(filename, references):
    """Load <batch>_doi.xml"""
    #refs = load_bib_blocks(file)

    def unescape(string):
        """Unescape XML string

        &lt; -> <
        &gt; -> >
        &amp; -> &
        """

        string = string.replace(r'&lt;', r'<')
        string = string.replace(r'&gt;', r'>')
        string = string.replace(r'&amp;', r'&')

        return string

    #we have to remove all illegal characters from crossref xml
    full_path = os.path.abspath(filename)
    path, filename = os.path.split(full_path)
    with open(full_path, 'r') as input:
        with open(os.path.join(path,"tmp"+filename), 'w') as output:
            for line in input:
                output.write(unescape(line))
    os.remove(full_path)
    os.rename(os.path.join(path, "tmp"+filename), os.path.join(path, filename))
    #Lets load the DOI.  First we assume unixref
    doc = minidom.parse(full_path)
    if doc.hasChildNodes():
        if doc.childNodes[0].nodeName == "doi_records":
            keys = doc.getElementsByTagName('doi_record')
        if doc.childNodes[0].nodeName == "crossref_result":
            keys = doc.getElementsByTagName('query')
    else:
        keys = []
        print "Invalid result file ... ignoring %s" % filename


    #build dictionary of references for faster lookup
    ref_dict = {}
    for ref in references:
        ref_dict[ref.ref_key] = ref
    
    s = 0
    ndoi = 0
    for key in keys:
        if key.hasAttribute('key'):
            refkey = key.getAttribute('key')
            refdoi = key.getElementsByTagName('doi')
            if refdoi:
                newdoi = refdoi[0].childNodes[0].nodeValue.strip()
                _ref = ref_dict[refkey]
                #print "{} -> {}".format(_ref.ref_doi, newdoi)
                if _ref.ref_doi != newdoi:
                    print "{} -- {}".format(_ref.ref_doi, newdoi)
                    _ref.setDOI(newdoi)
                    ndoi += 1
                s += 1
    
    print "Successfully set new DOI for {} references, {} of which did not match AMS".format(s, ndoi)



def queryMR(references, batch, ref_type='amsrefs', mode=2, debug=""):
    """Fetch the MR references for each reference"""
    
    total = len(references)
    for i, ref in enumerate(references):
        print "Reference {}/{}\tRequesting {}...".format(i, total, ref_type)
        ref.fetchMR(mode=mode, dataType=ref_type)
        print "{}\t{}".format(ref.ref_mr, ref.ref_doi)    

def main(argv):
    '''kick everything off'''

    if argv.dump is True:
        debug = logging.DEBUG
    else:
        debug = logging.INFO
        
    logging.basicConfig(filename=argv.batch+".log", level=debug, filemode='w')
        
    if argv.files:
        refs = util.load_bib_lines(argv.files)
    else:
        refs = cPickle.load(open(argv.batch, 'rb'))
        
    #Store the reference objects in a list
    #Loop through each file and get its references
    #Start the MR reference query
    if not argv.no_mr:
        queryMR(refs, argv.batch, ref_type=argv.mr_type, mode=argv.mode, debug=debug)
        
    if argv.doi:
        loadDoi(argv.doi, refs)
    else:
        response = raw_input("Should I generate Crossref XML queries (y/n)? ")
        if response.lower() == 'y':
            #get crossref config
            config = ConfigParser.SafeConfigParser()
            config.read("crossref.cfg")
            cross_cfg = {o:v for o, v in config.items("crossref")}
            
            file_list = query.QueryDOI(refs, argv.batch, cross_cfg)
            response = raw_input("Should I upload to Crossref right now (y/n)? ")
            if response.lower() == 'y':
                query.POST(file_list, cross_cfg['login_id'], cross_cfg['login_passwd'])
    
    print "\nSaving batch to file:", argv.batch
    cPickle.dump(refs, open(argv.batch, 'wb'))
    writeMRefFile(refs) 
    print "Log written to: {}.log".format(argv.batch)
    



if __name__ == "__main__":
    import argparse

    mrargs = argparse.ArgumentParser(description="Lookup MR References from doi")
    #mrargs.add_argument("--autodoi", action="store_true", help="Automatic DOI query (requires Crossref account)")
    mrargs.add_argument("--doi", action="store", default="", help="Add doi from file to batch (if possible)")
    mrargs.add_argument("--batch", metavar='batch', help="A unique batch name.  If no files specified will load batch.pkl ")
    mrargs.add_argument("--no-mr", action="store_true", help="Don't search for MR record")
    mrargs.add_argument("--mr-type", action="store", default="amsrefs", help="Format to request when querying MR numbers.")
    mrargs.add_argument("--mode", action="store", default=2, type=int, help="Query mode: 0 = Always use queried value; 1 = Always use existing value; 2 = Use queried value only when necessary")
    mrargs.add_argument("--dump", action="store_true", help="Dump query results to file (For debugging)")
    #mrargs.add_argument("--owritemr", action="store_true", help="Overwrite existing MR references with queried references", default=False)
    #mrargs.add_argument("--owritedoi", action="store_true", help="Overwrite existing DOI references with queried references", default=False)
    #mrargs.add_argument("--output", action='store', help="Alternative output filename")
    mrargs.add_argument('files', metavar='files', nargs='*', help='TeX files to process')

    main(mrargs.parse_args())
