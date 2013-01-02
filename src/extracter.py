#!usr/bin/python2
#-*-code = utf-8-*-

import os
import re
import ipdb
import itertools
from nltk.tree import *
from nltk.featstruct import FeatStruct,Feature
from collections import deque
from copy import deepcopy

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
            line = ftree.read().replace('=H','[+head]').replace('$', 'S')# to avoid the conflicts from featurestructre
            line = re.sub(r'[,.]( [,.])', 'Pu\g<1>', line)# NLTK featstruct cannot deal with punctuation
            align_line = alfile.readline()
            #read in aligment information
            alignment = self._read_alignment(align_line)
            #pt = ParentedTree.parse(line)
            pt = ParentedTree.parse(line, parse_node=FeatStruct)
            self._grouping(pt, alignment)
            #pt.draw()
            #print pt
            print self._get_head_group(pt)
            #the last punctuation is trivial
            pt[0].pop()
            pt.draw()
            return pt


    #def _annotate_help(self, tree):
    #    '''
    #    annotate help function.
    #    input: nltk tree structure
    #    output: modified nltk tree structure with annotation of node type
    #    '''
    #    if tree.height() <=2: 
    #        tree.node['type']='subs'
    #    else:
    #        iterrange = itertools.islice(tree.subtrees(), 1, None)
    #        for t in iterrange:
    #            pass
        

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
        if (tree.height() == 2 and isinstance(tree[0], str)) or \
                tree.height() == 1:
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
            if self._is_wellformed(currenttree):
                # we've found a nice tree which can be added to the grammar! cool!
                print "found good tree"
                #currenttree.draw()
                extracted_tree.append(currenttree)
            else:
                self._detect_conj(currenttree, agenda, extracted_tree)
                if self._detect_adjunct(currenttree, currenttree, agenda, extracted_tree):
                    continue
                self._detect_subs(currenttree, agenda, extracted_tree)
            #TEST

        for t in extracted_tree:
            t.draw()
            
    def _detect_adjunct(self, annotated_tree, root, agenda, extracted_tree):
        '''
        try to extract the adjunction part out of tree bones.
        input: a nltk ParentedTree
        output: an adjunction tree which will be added to agenda for further examination
                and a left tree bone which will be also added to agenda
        '''
        if annotated_tree.height() == 1 or \
                ( annotated_tree.height()==2 and isinstance(annotated_tree[0], str)):
                return False 
        else:
            # detect those adjuct tree where the adjuction happens at the root
            if self._detect_adjunct_help(annotated_tree, root, agenda, extracted_tree) == True:
                return True
            else:
                for child in annotated_tree[0:-1]:
                    self._detect_adjunct(child, root, agenda, extracted_tree)

    def _detect_adjunct_help(self, annotated_tree, root, agenda, extracted_tree):
        #ipdb.set_trace()
        pos = annotated_tree.node[Feature('type')]
        # we assume that there is no wrap adjuction tree in our grammar
        # so the adjuction either happens on the most left child or most right childtree
        # and every time we find a new tree, one normal tree and one adjuction tree will be constructed
        # to be fed into the agenda
        isadjunct = False
        leftmost = annotated_tree[0]
        rightmost = annotated_tree[-1]
        leftgo = not isinstance(leftmost, str) and leftmost.height() > 1
        rightgo = not isinstance(rightmost, str) and rightmost.height() > 1 
        while  leftgo or rightgo:
            if leftgo:
                if leftmost.node[Feature('type')] == pos and leftmost.node.get('head') == True:
                    # candidate adjuction node
                    if self._is_well_partitioned(annotated_tree, leftmost):
                        # it's really adjuction node
                        # 1. deepcopy it and add substitute to the root
                        # 2. deepcopy the whole tree, replace found node as a adjuct hole
                        isadjunct = True

                        holetree = leftmost.copy(deep=True)
                        newadjunctwhole = ParentedTree(deepcopy(holetree.node), [])
                        newadjunctwhole.node['adj'] = True
                        newadjunctwhole.node['group'] = set()
                        leftmost.parent()[leftmost.parent_index()] = newadjunctwhole
                        # copy the adjuct tree
                        adjuncttree = annotated_tree.copy(deep=True)
                        adjuncttree.node['adj'] = True
                        # when the adjuction is not at the root, subsitute the whole in
                        if not annotated_tree is root:
                            annotated_tree.parent()[annotated_tree.parent_index()] = newadjunctwhole
                            # put root tree in the agenda
                            self._grouping_help(root)
                            agenda.append(root)
                        # put new adjucttree in the agenda
                        self._grouping_help(adjuncttree)
                        print "adding adjucttree"
                        #adjuncttree.draw()
                        agenda.append(adjuncttree)
                        self._grouping_help(holetree)
                        print "adding holetree"
                        #holetree.draw()
                        agenda.append(holetree)
                        break
                leftmost = leftmost[0]
                leftgo = not isinstance(leftmost, str) and leftmost.height() > 1
            if rightgo:
                if rightmost.node[Feature('type')] == pos and rightmost.node.get('head') == True:
                    if self._is_well_partitioned(annotated_tree, rightmost):
                        isadjunct = True
                        holetree = rightmost.copy(deep=True)
                        newadjunctwhole = ParentedTree(deepcopy(holetree.node), [])
                        newadjunctwhole.node['adj'] = True
                        newadjunctwhole.node['group'] = set()
                        rightmost.parent()[rightmost.parent_index()] = newadjunctwhole
                        # copy the adjuct tree
                        adjuncttree = annotated_tree.copy(deep=True)
                        adjuncttree.node['adj'] = True
                        # subsitute the whole in
                        if not annotated_tree is root:
                            annotated_tree.parent()[annotated_tree.parent_index()] = newadjunctwhole
                            # put root tree in the agenda
                            self._grouping_help(root)
                            agenda.append(root)
                        # put new adjucttree in the agenda
                        self._grouping_help(adjuncttree)
                        agenda.append(adjuncttree)
                        self._grouping_help(holetree)
                        agenda.append(holetree)
                        break
                rightmost = rightmost[-1]
                rightgo = not isinstance(rightmost, str) and rightmost.height() > 1
        return isadjunct


    def _is_well_partitioned(self, annotated_tree, childtree):
        '''detect whether the childtree is well seperated from it's siblings
        input: 
            annotated_tree: the tree where childtree lies
            childtree: the tree which needs to tested
        '''
        rightsib = childtree.right_sibling()
        leftsib = childtree.left_sibling()
        othergroup = set()
        #ipdb.set_trace()
        while rightsib != None:
            othergroup.update(rightsib.node['group'])
            rightsib = rightsib.right_sibling()
        while leftsib != None:
            othergroup.update(leftsib.node['group'])
            leftsib = leftsib.left_sibling()
        if othergroup.intersection( childtree.node['group']):
            return False
        else:
            return True


    def _detect_subs(self, annotated_tree, agenda, extracted_tree):
        '''
        try to extract a vertebral tree which should only span on one group
        the leftover will be added to agenda
        '''
        expected_group = self._get_head_group(annotated_tree)
        self._detect_subs_help(annotated_tree, annotated_tree, expected_group, agenda)
        # the left annotated_tree is a substitution tree
        # update the group information and put it in to extracted_tree 
        self._grouping_help(annotated_tree)
        #print "adding subtree to extracted_tree"
        #annotated_tree.draw()
        extracted_tree.append(annotated_tree)

    def _detect_subs_help(self, annotated_tree, root, expected_group, agenda):
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
                    self._detect_subs_help(annotated_tree[i], root, expected_group, agenda)
            else:
                # find a pure unrelated node, needs to cut and add to agenda
                # the way deepcopy of nltk.ParentedTree works is a little strange
                #add current node to agenda
                agenda.append(annotated_tree.copy(deep=True))
                subs_tree = ParentedTree(deepcopy(annotated_tree.node), [])
                subs_tree.node['subs'] = True
                subs_tree.node['group'] = set()
                #update current node
                root[annotated_tree.treeposition()] = subs_tree
                
    def _detect_conj(self, annotated_tree, agenda, extracted_tree):
        self._detect_conj_help(annotated_tree, annotated_tree, agenda, extracted_tree)
        # update grouping information
        self._grouping_help(annotated_tree)

    def _detect_conj_help(self, annotated_tree, root, agenda, extracted_tree):
        '''
        detect conjunction tree, and it requires special treatment.
        '''
        if (annotated_tree.height() == 2 and isinstance(annotated_tree[0], str)) or annotated_tree.height() == 1:
            return
        else:
            if self._is_conj_tree(annotated_tree):
                conjtree = annotated_tree.copy(deep=True)
                subs_conjtree = ParentedTree(deepcopy(annotated_tree.node), [])
                subs_conjtree.node['subs'] = True
                subs_conjtree.node['group'] = set()
                root[annotated_tree.treeposition()] = subs_conjtree

                # deal with conjtree
                for i in range(len(conjtree)):
                    if not (conjtree[i][0] == ',' or conjtree[i].node[Feature('type')] == 'CC'):
                        # needs to be substitued
                        agenda.append(conjtree[i].copy(deep=True))
                        subs_tree = ParentedTree(deepcopy(conjtree[i].node), [])
                        subs_tree.node['subs'] = True
                        subs_tree.node['group'] = set()
                        conjtree[i] = subs_tree
                #update the grouping information of conjtree
                self._grouping_help(conjtree)
                extracted_tree.append(conjtree)
            else:
                for i in range(len(annotated_tree)):
                    self._detect_conj_help(annotated_tree[i], root, agenda, extracted_tree)

        
    def _is_conj_tree(self, annotated_tree):
        for i in range(len(annotated_tree)):
            if annotated_tree[i].node[Feature('type')] == 'CC':
                return True
        return False
    
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
                if(annotated_tree[i].node.get('head') == True):
                    # find the head child
                    # but sometime we've already processed the head node,
                    # for example, in adjuction tree, the head node will be extracted,
                    # the left tree bone will be without head information
                    if annotated_tree[i].node['group']: # if it's not empty
                        find = True
                        headgroup = self._get_head_group(annotated_tree[i])
                        break
                    else:
                        # it means we meet one node which was head but now is empty:
                        annotated_tree[i].node['head'] = False # update the head information
            if find == False:
                # in some cases, Stanford parser doesn't provide any head information, needs special treatment
                # we choose return 0, which indicate that some head information is missing
                # @TODO maybe it's more convenient to set a default head when head information is missing
                for i in range(len(annotated_tree)):
                    if annotated_tree[i].node['group']:
                        annotated_tree[i].node['head'] = True # set the first non-empty child as head
                        headgroup = self._get_head_group(annotated_tree[i])
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
    #fpath = dpath + 'fixed/ex21a.20.pst-heads-fixed'
    #alpath = dpath + 'alignments/ex21a.20.ali'
    for root, dirs, files in os.walk(dpath + 'fixed-test'):
        for f in files:
            print f
            m = re.match(r'(.*?)\.pst-heads-fixed', f)
            if m:
                fpath = dpath + 'fixed/' + m.group()
                alpath = dpath + 'alignments/' + m.group(1) + '.ali'
                at = ltge._annotate(fpath, alpath)
                ltge.extract(at)


if __name__ == '__main__':
    main()
