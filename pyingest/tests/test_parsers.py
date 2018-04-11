"""
Test parsers
"""

import unittest
import sys, os
import glob
import json
from pyingest.parsers import zenodo
from pyingest.parsers import arxiv
from pyingest.parsers import apsjats


class TestZenodo(unittest.TestCase):

    def setUp(self):
        stubdata_dir = os.path.join(os.path.dirname(__file__), '../../test_data/stubdata')
        self.inputdocs = glob.glob(os.path.join(stubdata_dir, 'input/zenodo*'))
        self.outputdir = os.path.join(stubdata_dir, 'parsed')
        sys.stderr.write("test cases are: {}\n".format(self.inputdocs))

    def test_zenodo_parser(self):
        parser = zenodo.ZenodoParser()
        for file in self.inputdocs:
            # this will raise exceptions if something is wrong
            with open(file, 'r') as fp:
                document = parser.parse(fp)
                self.assertIsNotNone(document, "%s: error reading doc" % file)
            basefile = os.path.basename(file)
            target = os.path.join(self.outputdir, basefile + '.json')
            # save temporary copy of data structure
            target_saved = target + '.parsed'
            with open(target_saved, 'w') as fp:
                json.dump(document, fp, sort_keys=True, indent=4)

            ok = False
            if os.path.exists(target):
                with open(target, 'r') as fp:
                    shouldbe = json.load(fp)
                    self.assertDictEqual(shouldbe, document, "results differ from %s" % target)
                    ok = True
            else:
                sys.stderr.write("could not find shouldbe file %s\n" % target)

            if ok:
                os.remove(target_saved)
            else:
                sys.stderr.write("parsed output dumped in %s\n" % target_saved)



class TestArxiv(unittest.TestCase):

    def test_bad_xml(self):
        with self.assertRaises(arxiv.EmptyParserException):
            with open('test_data/arxiv.test/readme.txt','rU') as fp:
                parser = arxiv.ArxivParser()
                document = parser.parse(fp)
 
    def test_parsing(self):
        shouldbe = {'authors':u'Luger, Rodrigo; Lustig-Yaeger, Jacob; Agol, Eric',
                    'title':u'Planet-Planet Occultations in TRAPPIST-1 and Other Exoplanet Systems',
                'bibcode':u'2017arXiv171105739L'}
        with open('test_data/arxiv.test/oai_ArXiv.org_1711_05739','rU') as fp:
            parser = arxiv.ArxivParser()
            document = parser.parse(fp)
        for k in shouldbe.keys():
            self.assertEqual(shouldbe[k],document[k])
        shouldbe['title'] = 'Paper that has nothing to do with TRAPPIST-1'
        self.assertNotEqual(shouldbe['title'],document['title'])

    def test_unicode_init(self):
        shouldbe = {'bibcode':u'2009arXiv0901.2443O'}
        with open('test_data/arxiv.test/oai_ArXiv.org_0901_2443','rU') as fp:
            parser = arxiv.ArxivParser()
            document = parser.parse(fp)
            self.assertEqual(document['bibcode'],shouldbe['bibcode'])

    def test_old_style_subjects(self):
        testfiles = ['test_data/arxiv.test/oai_ArXiv.org_astro-ph_9501013','test_data/arxiv.test/oai_ArXiv.org_math_0306266','test_data/arxiv.test/oai_ArXiv.org_hep-th_0408048','test_data/arxiv.test/oai_ArXiv.org_cond-mat_9706061'] 
        shouldbe = [{'bibcode':u'1995astro.ph..1013H'},{'bibcode':u'2003math......6266C'},{'bibcode':u'2004hep.th....8048S'},{'bibcode':u'1997cond.mat..6061A'}]
        for f,b in zip(testfiles,shouldbe):
            with open(f,'rU') as fp:
                parser = arxiv.ArxivParser()
                document = parser.parse(fp)
                self.assertEqual(document['bibcode'],b['bibcode'])


class TestAPSJATS(unittest.TestCase):

    def test_unicode_initial(self):
        testfile = 'test_data/stubdata/input/apsjats_10.1103.PhysRevB.96.081117.fulltext.xml'
        shouldbe = {'bibcode': '2017PhRvB..96h1117S'}
        with open(testfile,'rU') as fp:
            parser = apsjats.APSJATSParser()
            document = parser.parse(fp)
        self.assertEqual(document['bibcode'],shouldbe['bibcode'])
