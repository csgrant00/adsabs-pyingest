#!/usr/bin/env python

import bs4
from bs4 import Comment
from collections import OrderedDict
from default import BaseBeautifulSoupParser
from pyingest.config.config import *
import re
import copy


class NoSchemaException(Exception):
    pass


class WrongSchemaException(Exception):
    pass


class UnparseableException(Exception):
    pass


class JATSParser(BaseBeautifulSoupParser):

    def __init__(self):
        pass

    def _detag(self, r, tags_keep, **kwargs):
        newr = bs4.BeautifulSoup(unicode(r), 'lxml')
        try:
            tag_list = list(set([x.name for x in newr.find_all()]))
        except Exception, err:
            tag_list = []
        for t in tag_list:
            if t in JATS_TAGS_DANGER:
                oldr = None
                while oldr != newr:
                    try:
                        oldr = copy.deepcopy(newr)
                        newr.find(t).decompose()
                    except Exception, err:
                        pass
            elif t in tags_keep:
                oldr = None
                while oldr != newr:
                    try:
                        oldr = copy.deepcopy(newr)
                        newr.find(t).contents
                    except Exception, err:
                        pass
            else:
                oldr = None
                while oldr != newr:
                    try:
                        oldr = copy.deepcopy(newr)
                        newr.find(t).unwrap()
                    except Exception, err:
                        pass
        newr = unicode(newr)

        # deal with CDATA:
        cdata_pat = r'(\<\?CDATA)(.*?)(\?\>)'
        cdata = re.findall(cdata_pat, newr)
        for s in cdata:
            s_old = ''.join(s)
            s_new = s[1]
            newr = newr.replace(s_old, s_new)

        # amp_pat = r'(?<=&amp\;)(.*?)(?=\;)'
        amp_pat = r'(&amp;)(.*?)(;)'
        amp_fix = re.findall(amp_pat, newr)
        for s in amp_fix:
            s_old = ''.join(s)
            s_new = '&' + s[1] + ';'
            newr = newr.replace(s_old, s_new)

        newr = newr.replace(u'\n', u' ').replace(u'  ', u' ')
        newr = newr.replace('&nbsp;', ' ')

        return newr

    def resource_dict(self, fp, **kwargs):
        d = self.bsfiletodict(fp, **kwargs)
        r = self.bsstrtodict(unicode(d.article), **kwargs)
        return r

    def parse(self, fp, **kwargs):

        output_metadata = dict()

        document = self.resource_dict(fp, **kwargs)
        r = document.front

        try:
            article_meta = r.find('article-meta')
            journal_meta = r.find('journal-meta')
        except Exception, err:
            return {}

        back_meta = document.back

        base_metadata = {}

# Title:
        try:
            title = article_meta.find('title-group').find('article-title')
        except Exception, err:
            pass
        try:
            title.xref.extract()
        except Exception, err:
            pass
        try:
            title.fn.extract()
        except Exception, err:
            pass
        base_metadata['title'] = (
            self._detag(title, JATS_TAGSET['title']).strip())

# Abstract:
        try:
            abstract = article_meta.abstract.p
        except Exception, err:
            pass
        else:
            try:
                for element in abstract(text=lambda text: isinstance(text, Comment)):
                    element.extract()
            except Exception, err:
                pass
            else:
                abstract = (
                    self._detag(abstract, JATS_TAGSET['abstract']))
            base_metadata['abstract'] = abstract


# Authors and Affiliations:
        # Set up affils storage
        affils = OrderedDict()

        # Author notes/note ids
        try:
            notes = article_meta.find('author-notes').find_all('fn')
        except Exception, err:
            pass
        else:
            for n in notes:
                n.label.decompose()
                key = n['id']
                note_text = self._detag(n, JATS_TAGSET['affiliations'])
                affils[key] = note_text.strip()

        # Affils/affil ids
        try:
            affil = article_meta.find('contrib-group').find_all('aff')
        except Exception, err:
            pass
        else:
            for a in affil:
                try:
                    a.label.decompose()
                except Exception, err:
                    pass
                key = a['id']
                ekey = ''
                try:
                    email_array = []
                    email_a = a.find_all('ext-link')
                    for em in email_a:
                        if em['ext-link-type'] == 'email':
                            address = self._detag(em, (
                                JATS_TAGSET['affiliations']))
                            address_new = "<EMAIL>" + address + "</EMAIL>"
                            ekey = em['id']
                            if ekey is not '':
                                affils[ekey] = address_new
                    while a.find('ext-link') is not None:
                        a.find('ext-link').extract()
                except Exception, err:
                    pass

                aff_text = self._detag(a, JATS_TAGSET['affiliations'])
                affils[key] = aff_text.strip()
                # if ekey is not '':
                #     affils[ekey] = address_new

        # Author name and affil/note lists:
        try:
            authors = article_meta.find('contrib-group').find_all('contrib')
        except Exception, err:
            pass
        else:
            base_metadata['authors'] = []
            base_metadata['affiliations'] = []
            for a in authors:

                # ORCIDs
                orcid_out = None
                try:
                    # orcids = a.find_all('ext-link')
                    orcids = a.find('ext-link')
                    try:
                        if orcids['ext-link-type'] == 'orcid':
                            o = self._detag(orcids, [])
                            orcid_out = "<ID system=\"ORCID\">" + o + "</ID>"
                    except Exception, err:
                        pass
                except Exception, err:
                    pass

                # Author names
                if a.find('surname') is not None:
                    surname = self._detag(a.surname, [])
                else:
                    surname = 'Anonymous'
                if a.find('prefix') is not None:
                    prefix = self._detag(a.prefix, [])+' '
                else:
                    prefix = ''
                if a.find('suffix') is not None:
                    suffix = ' '+self._detag(a.suffix, [])
                else:
                    suffix = ''
                if a.find('given-names') is not None:
                    given = self._detag(a.find('given-names'), [])
                else:
                    given = ''
                forename = prefix+given+suffix
                if forename == '':
                    base_metadata['authors'].append(surname)
                else:
                    base_metadata['authors'].append(surname + ', ' + forename)

                # Author affil/note ids
                aid = a.find_all('xref')
                if len(aid) > 0:
                    aid_str = ' '.join([x['rid'] for x in aid])
                    aid_arr = aid_str.split()
                else:
                    aid_arr = []

                try:
                    new_aid_arr = []
                    for a in affils.keys():
                        if a in aid_arr:
                            new_aid_arr.append(a)
                    aid_arr = new_aid_arr

                    aff_text = '; '.join(affils[x] for x in aid_arr)
                    aff_text = aff_text.replace(';;', ';').rstrip(';')
                    aff_text = aff_text.replace('; ,', '').rstrip()

                    # Got ORCID?
                    if orcid_out is not None:
                        aff_text = aff_text + '; ' + orcid_out
                    base_metadata['affiliations'].append(aff_text)
                except Exception, errrror:
                    if orcid_out is not None:
                        base_metadata['affiliations'].append(orcid_out)
                    else:
                        base_metadata['affiliations'].append('')

            if len(base_metadata['authors']) > 0:
                base_metadata['authors'] = "; ".join(base_metadata['authors'])
            else:
                del base_metadata['authors']

# Copyright:
        try:
            copyright = article_meta.find('copyright-statement')
        except Exception, err:
            pass
        else:
            base_metadata['copyright'] = self._detag(copyright, [])

# Keywords:
        try:
            keywords = article_meta.find('article-categories').find_all('subj-group')
        except Exception, err:
            keywords = []
        for c in keywords:
            try:
                if c['subj-group-type'] == 'toc-minor':
                    base_metadata['keywords'] = self._detag(c.subject, (
                        JATS_TAGSET['keywords']))
            except Exception, err:
                pass
        if 'keywords' not in base_metadata:
            try:
                keywords = article_meta.find('kwd-group').find_all('kwd')
                kwd_arr = []
                for c in keywords:
                    kwd_arr.append(self._detag(c, JATS_TAGSET['keywords']))
                if len(kwd_arr) > 0:
                    base_metadata['keywords'] = ', '.join(kwd_arr)
            except Exception, err:
                pass

# Volume:
        volume = article_meta.volume
        base_metadata['volume'] = self._detag(volume, [])

# Issue:
        issue = article_meta.issue
        base_metadata['issue'] = self._detag(issue, [])

# Journal name:
        try:
            journal = journal_meta.find('journal-title-group').find('journal-title')
            base_metadata['publication'] = self._detag(journal, [])
        except Exception, err:
            try:
                journal = journal_meta.find('journal-title')
                base_metadata['publication'] = self._detag(journal, [])
            except Exception, err:
                pass

# Journal ID:
        try:
            jid = journal_meta.find_all('journal-id')
        except Exception, err:
            jid = []
        for j in jid:
            if j['journal-id-type'] == 'publisher-id':
                base_metadata['pub-id'] = self._detag(j, [])

# DOI:
        try:
            ids = article_meta.find_all('article-id')
        except Exception, err:
            ids = []
        for d in ids:
            if d['pub-id-type'] == 'doi':
                base_metadata['properties'] = {'DOI': self._detag(d, [])}

# Pubdate:

        try:
            pub_dates = article_meta.find_all('pub-date')
        except Exception, err:
            pub_dates = []
        for d in pub_dates:
            try:
                a = d['publication-format']
            except KeyError:
                a = ''
            try:
                b = d['pub-type']
            except KeyError:
                b = ''
            try:
                pubdate = "/" + self._detag(d.year, [])
                try:
                    d.month
                except Exception, err:
                    pubdate = "00" + pubdate
                else:
                    try:
                        int(self._detag(d.month, []))
                    except Exception, errrr:
                        month_name = self._detag(d.month, [])[0:3].lower()
                        month = MONTH_TO_NUMBER[month_name]
                    else:
                        month = self._detag(d.month, [])
                    if month < 10:
                        month = "0"+str(month)
                    else:
                        month = str(month)
                    pubdate = month + pubdate
            except Exception, errrr:
                pass
            else:
                if (a == 'print' or b == 'ppub'):
                    base_metadata['pubdate'] = pubdate
                elif (a == 'electronic' or b == 'epub'):
                    try:
                        base_metadata['pubdate']
                    except Exception, err:
                        base_metadata['pubdate'] = pubdate

# Pages:

        fpage = article_meta.fpage
        if fpage is None:
            fpage = article_meta.find('elocation-id')
            if fpage is None:
                fpage = article_meta.pageStart
                if fpage is None:
                    del fpage
        try:
            fpage
        except NameError:
            pass
        else:
            lpage = article_meta.lpage
            if lpage is None:
                lpage = article_meta.pageEnd
                if lpage is None:
                    del lpage
            else:
                if lpage == fpage:
                    del lpage
            try:
                lpage
            except NameError:
                base_metadata['page'] = self._detag(fpage, [])
            else:
                base_metadata['page'] = self._detag(fpage, []) + "-" + (
                    self._detag(lpage, []))

# References (now using back_meta):
        if back_meta is not None:
            try:
                ref_results = back_meta.find('ref-list').find_all('ref')
                print "NUMBER OF REFERENCES: %s"%len(ref_results)
                ref_results = ref_results
#               print ref_results
                for r in ref_results:
                    print "TYPE: %s"%type(r)
                    print r.contents
                #   s = unicode(r)
                #   print s.strip('\n')
            except Exception, err:
                print "References:", err
            else:
                base_metadata['references'] = 'lol'

#           for ref in reflist:
#               x = ref.find('ext-link')
#               if x is not None:
#                   print ref.find('ext-link')
#                   pass
#               else:
#                   print "uh oh",unicode(ref)

        output_metadata = base_metadata
        return output_metadata
