__author__ = 'grout'

from sys import exit
from xml.etree import cElementTree as cET
import ConfigParser
import util

def main(argv):

    #check for email address in ConfigFile if no email given on commandline
    if not argv.email:
        doiConfig = ConfigParser.SafeConfigParser()
        try:
            doiConfig.read('./crossref.cfg')
            argv.email = doiConfig.get('crossref', 'email')
        except:
            print "Need an email address!"
            exit()

    if not argv.batch:
        print "Need a batch name!"
        exit()

    refs = util.load_bib_lines(argv.files, argv.decomp)

    writeToQuery(refs, argv.email, argv.batch)


def buildDOIQuery(ref):
    qroot = cET.Element("query", {'enable-multiple-hits':'multi_hit_per_rule', 'list-components':'false', 'expanded-results':'false', 'key':str(ref.ref_key)})

    def escape(string):
        """Escape illegal XML characters

        & -> &amp;
        < -> &lt;
        > -> &gt;
        """

        string = string.replace(r'&', r'&amp;')
        string = string.replace(r'<', r'&lt;')
        string = string.replace(r'>', r'&gt;')
        return string

    fields = []
    if hasattr(ref, 'decomp'):
        #we have a decomposed ref
        try:
            author = cET.Element("author", {'search-all-authors':'false'})
            author.text = escape(ref.decomp['author'][0].split()[-1])
            fields.append(author)
        except:
            pass

        try:
            art_title = cET.Element("article_title", {'match':'fuzzy'})
            art_title.text = escape(ref.decomp['article_title'].replace('\n', ' '))
            fields.append(art_title)
        except:
            pass

        try:
            title = cET.Element("%s_title"%ref.decomp['type'])
            title.text = escape(ref.decomp['title'].replace('\n', ' '))
            fields.append(title)
        except:
            pass

        try:
            #print "Adding first page"
            fpage = cET.Element("first_page")
            fpage.text = str(ref.decomp['first_page'])
            fields.append(fpage)
        except:
            pass

        try:
            #print "Adding Volume"
            vol = cET.Element("volume")
            vol.text = str(ref.decomp['volume'])
            fields.append(vol)
        except:
            pass

        try:
            #print "Adding year"
            year = cET.Element("year")
            year.text = str(ref.decomp['year'])
            fields.append(year)
        except:
            pass

    else:
        citation = cET.Element("unstructured_citation")
        citation.text = escape(ref.ref_str.strip())
        fields.append(citation)


    qroot.extend(fields)
    return qroot

def writeToQuery(references, email, batch):
    #Write all references to "<batch>_query.xml"

    filename = "%s_query.xml" % batch

    print "Writing XML File (%s)" % filename

    #generate header
    header = cET.Element("query_batch", {'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'version':'2.0', 'xmlns':'http://www.crossref.org/qschema/2.0', 'xsi:schemaLocation':'http://www.crossref.org/qschema/2.0 http://www.crossref.org/qschema/crossref_query_input2.0.xsd'})

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

    for ref in references:
        #print "%s\t%s" % (ref, ref.ref_key)
        ret = buildDOIQuery(ref)
#        print "Received",ret
        body.append(ret)
    header.append(body)

#    print cET.tostring(header, 'UTF-8')
    with open(filename, "w") as ofile:
        #ofile.write('<?xml version = "1.0" encoding="UTF-8"?>\n')
        ofile.write(cET.tostring(header, 'UTF-8'))

if __name__ == "__main__":
    import argparse
    doiparser = argparse.ArgumentParser(description="CrossRef DOI XML Query generator", prog='doiquery')

    #arguments
    # --batch=<name>
    # --email=<name>
    # --decomp (bool)
    # <filenames>

    doiparser.add_argument('--batch', action='store', help='Batch query name')
    doiparser.add_argument('--email', action='store', help='Email address associated with XML query')
    doiparser.add_argument('--decomp', action='store_true', help='Attempt to decompose references.', default=True)
    doiparser.add_argument('files', metavar='files', nargs='+', help='TeX files to process')


    main(doiparser.parse_args())
