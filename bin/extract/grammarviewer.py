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

    def view(self, s):
        s = re.sub(r"set\(\[([\d, ]*)\]\)", r"{\g<1>}", s)
        print s
        #tree = ParentedTree.parse(s, node_pattern=r"\w*?\[.*?\]", parse_node=buildfeatstruct)
        tree = ParentedTree.parse(s, node_pattern=r"\w*?\[.*?\]", parse_node=FeatStruct)
        tree.draw()

    def read_gram_line(self, grammarfile):
        # parse the file

        s = []
        gram_str_list = []
        for line in grammarfile:
            if re.match(r"^\[.*\]$", line):
                print line
            else:
                for c in line:
                    if c == '(':
                        s.append(0)
                        gram_str_list.append(c)
                    elif c == ')':
                        s.pop()
                        gram_str_list.append(c)
                        if not s:
                            self.view(''.join(gram_str_list))
                            gram_str_list = []
                    elif s:
                        gram_str_list.append(c)

def main():
    import sys
    parser = argparse.ArgumentParser(description='Draw the tree according to grammar file')
    parser.add_argument("filename", nargs='?', default=sys.stdin, type=argparse.FileType('r'), help="The name of grammar file, stdin will be used if left open")
    args = parser.parse_args()
    print args.filename
    viewer = GrammarViewer()
    viewer.read_gram_line(args.filename)

if __name__ == '__main__':
    main()
