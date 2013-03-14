import util

def firstpage(pages):
    """Extract first page number from the PAGES field"""
    return pages[:pages.find('--')]

def issn(issn_num):
    issn_num = issn_num.replace('-', '')
    
    if len(issn_num) == 7:
        return issn_num + "X"
    else:
        return issn_num
    
def author(aut):
    aut = util.escape_replace(aut, "~", " ", escape="\\")
    return aut[aut.rfind(" "):].strip()