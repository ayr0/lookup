__author__ = 'grout'

import re
import os
import ConfigParser
from xml.dom import minidom
from getpass import getpass
from xml.etree import cElementTree as cET
from RefObj import RefObj
import util


def main(argv):
    '''kick everything off'''
    #argv is a argparse Namespace instance


    if argv.autodoi is True:
        #need to get crossref account info
        #we look for a config file
        #or we prompt if no config file is found in current directory

        doi_config = ConfigParser.SafeConfigParser()
        cref_user, cref_passwd = None, None
        try:
            doi_config.read('./crossref.cfg')
            cref_user = doi_config.get('crossref', 'user')
            cref_passwd = doi_config.get('crossref', 'password')
        except ConfigParser.Error:
            cref_user = raw_input("Crossref Username: ")
            cref_passwd = getpass()
        except:
            print "Unable to verify Crossref account.  Ignoring --auto flag"
            print "Please create a crossref.cfg file with user name and password"
            argv.autodoi = False


    #Store the reference objects in a list
    #Loop through each file and get its references
    refs = util.load_bib_lines(argv.files, False)
    #Start the MR reference query
    if not argv.no_mr:
        queryMR(refs, overwrite=argv.owritemr)

    if argv.autodoi is True:
        queryDOI(refs, cref_user, cref_passwd, overwrite=argv.owritedoi)
    else:
        #check for the existence of a doi file
        if os.path.exists(argv.doi):
            loadDoi(argv.doi, refs)

    writeMRefFile(refs)

def generateFileList(refs):
    """Generate a list of files that had the original references.

    The filename that contains a given reference is stored in the reference object.
    If we did a DOI query, there is no need to give files to mrquery"""
    files = []
    for ref in refs:
        if ref.ref_file not in files:
            files.append(ref.ref_file)
        else:
            continue
    return files

def writeMRefFile(references):
    """Write the references to another file."""

    files = generateFileList(references)
    for f in files:
        with open("%s_refs.tex" % os.path.splitext(f)[0], "w") as ofile:
            for ref in references:
            	if ref.ref_file == f:
                	ofile.write('%s\n\n' % ref._reformat(ref=ref.addRefs()))

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
    with open(filename, 'r') as input:
        with open("tmp"+filename, 'w') as output:
            for line in input:
                output.write(line.replace(r'&', r'&amp;'))
    os.remove(filename)
    os.rename("tmp"+filename, filename)
    #Lets load the DOI.  First we assume unixref
    doc = minidom.parse(filename)
    format = None
    if doc.hasChildNodes():
        if doc.childNodes[0].nodeName == "doi_records":
            keys = doc.getElementsByTagName('doi_record')
        if doc.childNodes[0].nodeName == "crossref_result":
            keys = doc.getElementsByTagName('query')
    else:
        keys = []
        print "Invalid result file ... ignoring %s" % filename


    #print "keys length %i" % len(keys)
    for key in keys:
        if key.hasAttribute('key'):
            refkey = key.getAttribute('key')
        else:
            continue

        #search for matching key in references
        for ref in references:
            if ref.ref_key == refkey:
                refdoi = key.getElementsByTagName('doi')
                if refdoi:
                    newdoi = refdoi[0].childNodes[0].nodeValue
                    ref.ref_doi = newdoi
    
    print "Successfully set DOI references"



def queryMR(references, overwrite=False):
    """Fetch the MR references for each reference"""
    [ref.fetchMR(overwrite=overwrite) for ref in references]

def queryDOI(references, user, passwd, overwrite=False):
    """Fetch the DOI references for each reference"""
    print user, passwd
    [ref.fetchDOI(user, passwd, overwrite=overwrite) for ref in references]



if __name__ == "__main__":
    import argparse

    mrargs = argparse.ArgumentParser(description="Lookup MR References from doi")
    mrargs.add_argument("--autodoi", action="store_true", help="Automatic DOI query (requires Crossref account)")
    mrargs.add_argument("--doi", metavar='batch', action="store", help="Add DOI references to final output")
    mrargs.add_argument("--no-mr", action="store_true", help="Don't search for MR record")
    mrargs.add_argument("--owritemr", action="store_true", help="Overwrite existing MR references with queried references", default=False)
    mrargs.add_argument("--owritedoi", action="store_true", help="Overwrite existing DOI references with queried references", default=False)
    #mrargs.add_argument("--output", action='store', help="Alternative output filename")
    mrargs.add_argument('files', metavar='files', nargs='+', help='TeX files to process')

    main(mrargs.parse_args())
