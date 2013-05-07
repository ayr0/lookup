"""Processors for different fields of a reference

These processors are used for each reference processed for crossref query
"""
import util

def firstpage(pages):
    """Extract first page number from the PAGES field"""
    return pages[:pages.find('--')]

def issn(issn_num):
    #Must match pattern \d{4}-?\d{3}[\dX]
    
    def tail(x):
        return x[:3].isdigit() and (x[3].isdigit() or x[3] == 'X')
    
    issn_num = issn_num.upper()
    
    if issn_num[:4].isdigit():
        if (issn_num[4] == '-' and tail(issn_num[5:])) or tail(issn_num[4:]):
            return issn_num
        else:
            return ""

        
def author(aut):
    aut = util.escape_replace(aut, "~", " ", escape="\\")
    return aut[aut.rfind(" "):].strip()