#! /usr/bin/python2.7
# -*- coding: utf-8 -*-
"""This class is a helper for merging skos thesauri. It is based on
rdflib (https://github.com/RDFLib)
Right now, this tool is more a proof of concept than a productive
tool.
USE WITH CAUTION
"""


from rdflib import ConjunctiveGraph, URIRef, Namespace, RDF, OWL
from nltk.stem.porter import PorterStemmer
import logging
import sys
import unicodedata
import string

__author__ = "Jana Hoerstermann, Nils Geisemeyer, Gregor Kneitschel"
__email__ = "firstname.lastname@fh-potsdam.de"
__version__ = "0.0.1-firstblood"
# firstblood, dominating, rampage, unstoppable
# godlike, whickedsick, ludacris, holyshit
__license__ = "GPL"
__status__ = "Prototype"


class Merger:
    SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
    EXA = Namespace('http://www.example.com/#')

    def __init__(self, files, verbose):
        """Create a new instance.
        init takes two paramters, **file** and **verbose**. **file** is a list
        of files that will become global to this class.
        **verbose** sets the level of logging. If set to none, the loglevel
        is ``warning`` and will never be called. Debug will set the
        loggerlevel to ``debug`` - this would get you a lot of information.
        File, screen and both will set the level to info and tell the logger
        where the output should go. The logfile is called ``parserLog.txt``.
        init also creates a resultgraph, that contains all thesauri and their
        mappings.
        :param files: list of thesauri
        :type files: list
        :param verbose: A string of (screen, file, both, none, debug)
        :type verbose: string
        """
        if verbose not in ('screen', 'file', 'both', 'none', 'debug'):
            sys.exit('Value of verbose must be screen, file, both, debug'
                     ' or none')
#         Creating a logging instance and
 #        enable different levels based on verbose
        self.logger = logging.getLogger()
        if verbose == 'none':
            self.logger.setLevel(logging.WARNING)
        elif verbose == 'debug':
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.formatter = logging.Formatter(
                         '%(asctime)s - %(levelname)s - %(message)s')
        self.log(output=verbose)
        self.logger.debug('Logger created')
        self.logger.debug('Initalizing global variables')
        #self.files = files  # List of input files
        self.porter = PorterStemmer()
        self.result = ConjunctiveGraph()  # Where it ends
        self.graphlist = self.parseGraphs(files)
        self.mergeFiles(self.graphlist)
        self.logger.debug('Got %s inputfiles' % (len(files)))
       # self.graph = {}  # contains the parsed input files
        self.logger.info('Merger initiated')
        self.addContext()
        self.reporting = {}
        self.reporting['equals'] = 0
        self.reporting['substrings'] = 0
        self.reporting['phrase'] = 0
        self.reporting['related'] = 0

    def log(self, output='both'):
        """this method creates a filehandle and a screenhandle for
        the logger. Depending on the output variable, it will call
        logToFile, to create the filehandle or logToScreen, to
        create the screenhandle, or both. If output is debug,
        log creates two handles as well. If output is none, nothing
        happens.

        Expected parameter: file, screen, both, debug, none"""
        def logToFile():
            """Create a filehandle for logging. The file is called
            parserLog.txt. Loglevel is set to debug, so both, info and
            debug will be written.
            TODO: User gets to decide filename and location
            """
            fh = logging.FileHandler('parserLog.txt')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(self.formatter)
            self.logger.addHandler(fh)

        def logToScreen():
            """Create screenhandle for logging. All logs get written
            onto screen. Loglevel is set to debug, so both, info and
            debug will be written.
            TODO: redundant?
            """
            scr = logging.StreamHandler()  # Print on screen
            scr.setLevel(logging.DEBUG)
            scr.setFormatter(self.formatter)
            self.logger.addHandler(scr)
        if output == 'both' or 'debug':
            logToFile()
            logToScreen()
        if output == 'file':
            logToFile()
        if output == 'screen':
            logToScreen()

    def parseGraphs(self, files):
        """This Method takes the input file names and
        parses them.
        return: graphs - a list of ConjunctiveGraphs
        """
        self.logger.info('Parsing the input files: %s' % (files))
        graphs = []
        for i in range(len(files)):
            graphs.append(ConjunctiveGraph('IOMemory'))
        for i in range(len(files)):
            graphs[i].parse(files[i], format='xml')
        self.logger.debug('Graphlist created. Length is %s' % (len(graphs)))
        return graphs

    def mergeFiles(self, graphs):
        """Calls the addContent-method on each graph in self.graph dictionary.
        This will write all graphs into one graph (the resultgraph)
        """
        self.logger.info('Merging inputfiles into resultgraph...')
        for i in range(len(graphs)):
            self.addContent(graphs[i])

    def addContext(self):
        """
        Adding the namespacebinding for SKOS and a custom namespace EXA.
        TODO: Own Method for custom NS binding?
        """
        self.result.bind('skos', Merger.SKOS)
        self.result.bind('exa', Merger.EXA)
        self.addToResult(Merger.EXA.distantMatch, RDF.type, OWL.ObjectProperty)


    def getLabels(self, graph):
        """getLabels takes a ConjunctiveGraph instance and finds all
        SKOS:prefLabel. It returns an dictionary with {uri:label}.
        param: graph - a ConjunctiveGraph instance
        return: compict - a dictionary of all {uri:label} for a graph
        """
        compdict = {}
        self.logger.info('Getting labels from %s' % (graph))
        for uri, label in graph.subject_objects(
                    URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")):
            compdict[uri] = label.toPython().strip().lower()
        return compdict

    def removeDiacritics(self, label):
        """
        This method uses unicodedata() to remove diacritics from a string
        TODO: Does this work without unicodedata?
        param: string
        return: string
        """
        label = ''.join((c for c in unicodedata.normalize('NFD', unicode(label)) if unicodedata.category(c) != 'Mn'))
        return label

    def removePunctuation(self, label):
        """This method removes punctuations. Right now, it will remove
        '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
        param: string
        return: string
        """
        for punct in string.punctuation:
            label = label.replace(punct," ")
        return label

    def stemWords(self, label):
        """This method stems a single word or a phrase
        param: string
        return: string
        """ 
        
        label = " ".join(self.porter.stem_word(word) for word in label.split(" "))
        return label

    def __broaders(self, uri, graph):
        """This "private" method is a generator over broaderTerms of a given URI in
        a given ConjunctiveGraph. Use getParents() to obtain the list of broaderTerms
        """
        for n in graph.transitive_objects(uri, URIRef('http://www.w3.org/2004/02/skos/core#broader')):
            if (uri==n):
                continue
        yield n

    def __narrowers(self, uri, graph):
        """This "private" method is a generator over narrowerTerms of a given URI in
        a given ConjunctiveGraph. Use getchildren() to obtain the list of narrowerTerms
        """
        for n in graph.transitive_objects(uri, URIRef('http://www.w3.org/2004/02/skos/core#narrower')):
            if (uri==n):
                continue
        yield n

    def getParents(self, uri, graph):
        list = []
        for n in self.__broaders(uri, graph):
            for label in graph.objects(n, URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")):
                list.append(label.toPython().strip().lower())
        return list

    def getChildren(self, uri, graph):
        list = []
        for n in self.__narrowers(uri, graph):
            for label in graph.objects(n, URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")):
                list.append(label.toPython().strip().lower())
        return list

    def isSameTerm(self, label1, label2):
        """returns true if two items are equal
        params: string
        """
        if label1 ==label2:
            self.logger.debug('Identical terms found %s - %s' % (label1, label2))
            return True

    def isSubstring(self, label1, label2):
        """returns true if one item is a substring of the other.
        params: string
        """
        if len(label1.split(' ')) == 1 and len(label2.split(' ')) == 1:
            # if both split-operations have returned
            # one word (were not successful)
            if (label1 in label2 or label2 in label1):
                self.logger.debug('Substring found for %s and %s'
                                  % (label1, label2))
                return True

    def isPhrase(self, label1, label2):
        """returns true if one item is a phrase containing the other item.
        params: string
        """
        if len(label1.split(' ')) > 1 or len(label2.split(' ')) > 1:
            # if one of the lists holds more than one word (is a phrase)
            for word in label1.split(' '):
                for word2 in label2.split(' '):
                    if word == word2:
                        return True

    def termSignatur(self, label):
        """This method will return the term signatur of phrase.
        It stems and sort the phrase.
        param: string
        return: string
        """
        return ''.join(sorted(self.porter.stem_word(word) for word in label.split(" ")))

    def isSameSig(self, label1, label2):
        if len(label1.split(' ')) > 1 and len(label2.split(' ')) > 1:
            label1 = self.termSignatur(label1)
            label2 = self.termSignatur(label2)
            if label1 == label2:
                return True

    def isConceptScheme(self, uri):
        """returns true if a uri is a SKOS:ConceptScheme
        TODO: Method for custom "type"-checking
        """
        i = 0
        for triple in self.result.triples((uri, RDF.type,
                                           Merger.SKOS.ConceptScheme)):
            i += 1
        if i > 0:
            self.logger.debug('Is a ConceptScheme: %s' % (uri))
            return True
        return False

    def addEquals(self, uri1, uri2):
        """addEquals takes two URIs and adds them to the resultgraph.
        if one of the URIs is a SKOS:ConceptScheme, the predicate will
        be EXA:distantMatch instead of SKOS:CloseMatch.
        """
        self.reporting['equals'] += 1
        if self.isConceptScheme(uri1) or self.isConceptScheme(uri2):
            self.logger.debug('Adding equal Concept - ConcepScheme relation')
            self.addToResult(uri1, Merger.EXA.distantMatch, uri2)
        else:
            self.logger.debug('Adding equal terms')
            self.addToResult(uri1, Merger.SKOS.closeMatch, uri2)

    def addRelated(self, uri1, uri2):
        """addEquals takes two URIs and adds them to the resultgraph.
        if one of the URIs is a SKOS:ConceptScheme, the predicate will
        be EXA:distantMatch instead of SKOS:CloseMatch.
        """
        self.reporting['related'] += 1
        if self.isConceptScheme(uri1) or self.isConceptScheme(uri2):
            self.logger.debug('Adding equal Concept - ConcepScheme relation')
            self.addToResult(uri1, Merger.EXA.distantMatch, uri2)
        else:
            self.logger.debug('Adding equal terms')
            self.addToResult(uri1, Merger.SKOS.semanticRelation, uri2)

    def addSubstrings(self, uri1, uri2):
        """addSubstrings takes two URIs and adds them to the resultgraph.
        if one of the URIs is a SKOS:ConceptScheme, the predicate will
        be EXA:distantMatch instead of SKOS:relatedMatch.
        """
        self.reporting['substrings'] += 1
        if self.isConceptScheme(uri1) or self.isConceptScheme(uri2):
            self.logger.debug('Adding substr Concept - ConcepScheme relation')
            self.addToResult(uri1, Merger.EXA.distantMatch, uri2)
        else:
            self.logger.debug('Adding substrings')
            self.addToResult(uri1, Merger.SKOS.relatedMatch, uri2)

    def addPhrase(self, uri1, uri2):
        """addPhrase takes two URIs and adds them to the resultgraph.
        if one of the URIs is a SKOS:ConceptScheme, the predicate will
        be EXA:distantMatch instead of SKOS:relatedMatch.
        """
        self.reporting['phrase'] += 1
        if self.isConceptScheme(uri1) or self.isConceptScheme(uri2):
            self.addToResult(uri1, Merger.EXA.distantMatch, uri2)
            self.logger.debug('Adding phrase Concept - ConcepScheme relation')
        else:
            self.logger.debug('Adding phrase')
            self.addToResult(uri1, Merger.SKOS.relatedMatch, uri2)

    def addToResult(self, s, p, o):
        """Adds a triple to the resultgraph"""
        self.result.add((s, p, o))

    def writeToFile(self, dest, ext):
        """Serializes the resultgraph into a file
        TODO: custom filename and format
        """
        self.logger.info('Writing output...')
        self.result.serialize(destination=dest, format=ext)
        self.logger.info('Done.')

    def addContent(self, graph):
        """Adds all triples from a graph to the resultgraph"""
        for s, p, o in graph:
            self.addToResult(s, p, o)
