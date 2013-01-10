#/usr/bin/python2
# -*- code=utf-8 -*-


import os
import argparse
import re
import thread
from multiprocessing import Pool
from nltk import ParentedTree
from nltk import FeatStruct

class GrammarViewer:
    ''' a small tool to view grammar extracted'''

    def __init__(self):
        '''default init function'''
        pass

    def view(self, grammarfile):
        s = ''
        p = Pool()
        for line in grammarfile.readlines():
            if line != '\n':
                if line[0] == '|':
                    print line
                else:
                    line = re.sub(r"set\(\[(\d*)\]\)", r"\g<1>", line)
                    line = re.sub(r", ", r",", line)
                    line = re.sub(r"group=,", r"", line)
                    #line = re.sub(r"set\(\[(.*?)\]\)", r"\g<1>", line)
                    s += line
            else:
                print s
                tree = ParentedTree.parse(s, parse_node=FeatStruct)
                tree.draw()
                s = ''

def main():
    parser = argparse.ArgumentParser(description='Draw the tree according to grammar file')
    parser.add_argument("filename", help="the name of grammar file")
    args = parser.parse_args()
    print args.filename
    viewer = GrammarViewer()
    with open(args.filename) as grammarfile:
        viewer.view(grammarfile)

if __name__ == '__main__':
    main()
