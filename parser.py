#! /usr/bin/python2.7
# -*- coding: utf-8 -*-#

from src.skostheme import Merger

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("input", nargs="+", help='Two or more inputfiles')
parser.add_argument("-o", "--output", required=True,
                    help='The output file (required)')
parser.add_argument("-f", default="xml",
                    choices=['xml', 'turtle', 'n3', 'nt', 'pretty-xml', 'trix'],
                    help='The output format, default is XML')
parser.add_argument("--verbose",
                    choices=['file', 'screen', 'both', 'none', 'debug'],
                    default='screen',
                    help='Set verbosity and determine output stream.\
                    File writes to parserLog.txt, screen writes to STDOUT\
                    and both writes to both. Disable using none. Debug is\
                    for debugging purposes only')
parser.add_argument('-s', action='store_true',
                    help='Use stemming')
parser.add_argument('-r', action='store_true',
                    help='remove diacritics and punctuations')
parser.add_argument('-c', action='store_true',
                    help='compare children (narrower terms)')
parser.add_argument('-p', action='store_true',
                    help='compare parents (broader terms)')
parser.add_argument("-i", action='store_true',
                    help='Map identical terms only ')
parser.add_argument("-t", action='store_true',
                    help='Map identical terms only ')
args = parser.parse_args()  # parse arguments

if (len(args.input) < 2):  # if there are less than 2 files
    sys.exit('Please specify at least TWO input files')
files = args.input
parser = Merger(files, verbose=args.verbose)


def recursiveCompare():
    """This function removes the first graph
    from the list of graphs and compares it to
    the other graphs. When finished, it starts
    over (i.e. recursuion9
    """
    startgraph = parser.graphlist.pop()
    for i in range(len(parser.graphlist)):
        dict1 = parser.getLabels(startgraph)
        dict2 = parser.getLabels(parser.graphlist[i])
        parser.logger.info('starting comparison...')
    #   if mode == 'i':
    #       self.logger.info('Searching only equal terms...')
    #   # for every label in both dicts
        for uri1, label1 in dict1.items():
            if(args.s):
                label1 = parser.stemWords(label1)
            if (args.r):
                label1 = parser.removeDiacritics(label1)
                label1 = parser.removePunctuation(label1)
            if (args.c):
                children1 = parser.getChildren(uri1, startgraph)
            if (args.p):
                parents1 = parser.getParents(uri1, startgraph)
            for uri2, label2 in dict2.items():
                if (args.r):
                    label1 = parser.removeDiacritics(label1)
                    label1 = parser.removePunctuation(label1)
                if(args.s):
                    label2 = parser.stemWords(label2)
                if (args.c):
                    children2 = parser.getChildren(uri2, parser.graphlist[i])
                if (args.p):
                    parents2 = parser.getParents(uri1, startgraph)
                if parser.isSameTerm(label1, label2):
                    parser.addEquals(uri1, uri2)
                    continue
                if (args.i):
                    continue
                if parser.isSubstring(label1, label2):
                    parser.addSubstrings(uri1, uri2)
                    continue
                if parser.isPhrase(label1, label2):
                    parser.addPhrase(uri1, uri2)
                    continue    
                if(args.t):
                    if parser.isSameSig(label1, label2):
                        parser.addPhrase(uri1, uri2)
                    continue
                if (args.c):
                    if (bool(set(children1) & set(children2))):
                        parser.addRelated(uri1, uri2)
                if (args.p):
                    if (bool(set(parents1) & set(parents2)) and
                         len(set(parents1) & set(parents2)) >= 3):
                        parser.addRelated(uri1, uri2)
            if len(parser.graphlist) > 1:
                recursiveCompare(parser.graphlist)

recursiveCompare()
parser.writeToFile(args.output, args.f)

for k, v in parser.reporting.iteritems():
    print v,' ',k,' found'
