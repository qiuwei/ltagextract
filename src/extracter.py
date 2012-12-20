#!usr/bin/python2
#-*-code = utf-8-*-

import os
import re
import itertools
from nltk.tree import *
from nltk.featstruct import FeatStruct
from collections import deque

class LtagExtractor:
    '''LtagExtractor which extract Tree adjoin grammar from stanford parse result'''
    def __init__(self):
        '''default init function'''
        pass

    
    def _annotate(self, tree_file, alignment_file):
        '''
        _annotate annotate the tree node to show the tree whether:
        1. is got form substitution
        2. is got from adjunction
        3. is got from conjunction 'x and y' or 'x, y and z'
        The result returned is a tree with annotation,
        The annotation convention is that:
        NP[type='subs', conj='y']:
        A NP which is got from substitution and it's a conjunction phrase;

        VP[type='adj', conj='n']:
        A VP which is got from adjunction and it's not a conjunction phrase;
        '''
        
        with open(tree_file) as ftree, open(alignment_file) as alfile:
            line = ftree.read().replace('=H','[+head]')# to avoid the conflicts from featurestructre
            line = re.sub(r'[,.]( [,.])', 'Pu\g<1>', line)# NLTK featstruct cannot deal with punctuation
            align_line = alfile.readline()
            #read in aligment information
            alignment = self._read_alignment(align_line)
            #pt = ParentedTree.parse(line)
            pt = ParentedTree.parse(line, parse_node=FeatStruct)
            self._grouping(pt, alignment)
            pt.draw()
            #print pt
            print self._get_head_group(pt)
            return pt


    def _annotate_help(self, tree):
        '''
        annotate help function.
        input: nltk tree structure
        output: modified nltk tree structure with annotation of node type
        '''
        if tree.height() <=2: 
            tree.node['type']='subs'
        else:
            iterrange = itertools.islice(tree.subtrees(), 1, None)
            for t in iterrange:
                pass
        

    def _grouping(self, tree, alignment):
        '''
        grouping function:
        add group information to nltk tree to help identify whehter a tree is *pure* or not
        input: nltk tree structure
        output: modified nltk tree with group information
        '''
        ip = 0 # position counter
        for l in alignment:
            ip -=1
            for k in l:
                ip += 1
                # i is the current postion
                # and i's group number is l[0]
                # we will find i's parent and update it's feature structure by adding group information
                # group information will be encoded as a set of integer
                tree[tree.leaf_treeposition(ip)[0:-1]].node['group'] = {int(l[0])}
        # the last node(period) doesn't belong to any group
        tree[tree.leaf_treeposition(ip)[0:-1]].node['group'] = set()
        self._grouping_help(tree)
    
    def _grouping_help(self, tree):
        #end of recursion, the group information is already inserted, do nothing
        if tree.height() <= 2:
            return
        else:
            #recursively get the group information from its children
            s = set() # intitalized current node's group feature
            iterrange = itertools.islice(tree.subtrees(), 1, None)
            for t in iterrange:
                self._grouping_help(t)
                s.update(t.node['group'])
            tree.node['group'] = s
         
    def _read_alignment(self, alignment_string):
        '''
        read in alightment configration, store it as a list of list.
        '''

        group = [l.split() for l in re.split(r"\]\s*\[", re.search(r'\[(.*)\]', alignment_string).group(1))]
        return group

    def extract(self, annotated_tree):
        '''
        read in annotated tree, extract etree.
        input: annotated tree
        ouput: etrees
        '''
        #initialize the agenda
        agenda =  deque()
        agenda.append(annotated_tree)

        extracted_tree = []

        #loop until agenda is empty
        while agenda:
            currenttree = agenda.popleft()
            print currenttree
            if self._is_wellformed(currenttree):
                # we've found a nice tree which can be added to the grammar! cool!
                extracted_tree.append(currenttree)
            else:
                self._detect_adjunct(currenttree, agenda)
                self._detect_subs(currenttree, agenda)
                self._detect_conj(currenttree, agenda)
            #TEST
            break

        for t in agenda:
            t.draw()

    def _detect_adjunct(self, annotated_tree, agenda):
        '''
        try to extract the adjunction part out of tree bones.
        input: a nltk ParentedTree
        output: an adjunction tree which will be added to agenda for further examination
                and a left tree bone which will be also added to agenda
        '''
        pass

    def _detect_subs(self, annotated_tree, agenda):
        '''
        try to extract a vertebral tree which should only span on one group
        the leftover will be added to agenda
        '''
        expected_group = self._get_head_group(annotated_tree)
        self._detect_subs_help(annotated_tree, expected_group, agenda)

    def _detect_subs_help(self, annotated_tree, expected_group, agenda):
        #if current node doesn't contain expected_group,
        # we can safely consider current node as a substitution node, 
        # and add it to our agenda
        if isinstance(annotated_tree, str) or annotated_tree.height() == 1:
            # no need to deal with frontier nodes
            return
        else:
            if expected_group in annotated_tree.node['group']:
                # the node is not *pure* enough, need to go deeper
                for i in range(len(annotated_tree)):
                    self._detect_subs_help(annotated_tree[i], expected_group, agenda)
            else:
                # find a pure unrelated node, needs to cut and add to agenda
                copytree = annotated_tree.copy()
                #add current node to agenda
                agenda.append(copytree)
                subs_tree = ParentedTree(annotated_tree.node, [])
                subs_tree.node['subs'] = True
                subs_tree.node['group'] = set()
                #update current node
                annotated_tree = subs_tree
                
    def _detect_conj(self, annotated_tree, agenda):
        '''
        try to detect whether annotated tree is a conjunction tree, it needs to be specially treated
        '''
        pass

    def _get_head_group(self, annotated_tree):
        '''
        we use a recursive strategy to extract grammar regarding to the root of input tree,
        the head can be considered as the projection of the root, or the lexicon anchor.
        we first get the group of head of root, then kick out all of elements in the tree in a greedy way.
        The trees which are kicked out will be put into a agenda to be processed.
        The left tree bones will be added to a return list.
        '''
        if (annotated_tree.height() == 2 and isinstance(annotated_tree[0], str)) or \
                annotated_tree.height() == 1:
            # here we want to get the head information
            # but the bad thing is the leaf type is str, so we can't use the same algorithm on leaves,
            # it's a dirty hack to guarantee that we stop before going to str leaves
            return list(annotated_tree.node['group'])[0] # retrieve the only element in the set
        else:
            find = False
            for i in range(len(annotated_tree)):
                if(annotated_tree[i].node.has_key('head')):
                    # find the head child
                    find = True
                    headgroup = self._get_head_group(annotated_tree[i])
                    break
            if find == False:
                # in some cases, Stanford parser doesn't provide any head information, needs special treatment
                # we choose return 0, which indicate that some head information is missing
                # @TODO maybe it's more convenient to set a default head when head information is missing
                headgroup = 0
            return headgroup
            
    def _is_wellformed(self, tree):
        '''
        decide whether a tree is well formed or not.
        A tree is well formed if and only if it only spans on one group.
        a well formed tree can be consider as legal in the grammar we want to extract.
        input: a nltk ParentedTree
        output: boolean
        '''
        #it only contains one element
        if len(tree.node['group']) == 1:
            return True
        return False



def main():
    ltge = LtagExtractor()
    dpath = os.path.expanduser('~/workspace/es.qiu.ltagextract/')
    fpath = dpath + 'fixed/ex21a.20.pst-heads-fixed'
    alpath = dpath + 'alignments/ex21a.20.ali'
    print fpath
    at = ltge._annotate(fpath, alpath)
    ltge.extract(at)


if __name__ == '__main__':
    main()
