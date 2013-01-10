#!usr/bin/python2
#-*-code = utf-8-*-

import os
import re
import itertools
import argparse
import sexprparse
from nltk.tree import *
from nltk.featstruct import FeatStruct,Feature
from collections import deque, defaultdict
from copy import deepcopy

class LtagExtractor:
    '''LtagExtractor which extract Tree adjoin grammar from stanford parse result'''
    # data structure to save extracted grammar
    gram = defaultdict(set)

    def __init__(self):
        '''default init function'''
        pass

    def output_gram(self, f):
        '''
        output the grammar to stdout
        '''
        for sem in self.gram:
            f.write(sem)
            f.write(os.linesep)
            for g in self.gram[sem]:
                if type(g) is str:
                    print g
                else:
                    f.write(g.pprint() + os.linesep)
            f.write(os.linesep)

    def _annotate(self, tree_file, align_syn):
        '''
        _annotate annotate the tree node with group information
        '''

        with open(tree_file) as ftree:
            line = ftree.read().replace('=H','[+head]').replace('$', 'S')# to avoid the conflicts from featurestructre
            line = re.sub(r'[,.]( [,.])', 'Pu\g<1>', line)# NLTK featstruct cannot deal with punctuation
            #read in aligment information
            #alignment = self._read_alignment(align_line)
            #pt = ParentedTree.parse(line)
            pt = ParentedTree.parse(line, parse_node=FeatStruct)
            self._grouping(pt, align_syn)
            #pt.draw()
            #print pt
            #print self._get_head_group(pt)
            #the last punctuation is trivial
            pt[0].pop()
            #pt.draw()
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
        add group information to nltk tree to help identify whether a tree is *pure* or not
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
        read in alignment configuration, store it as a list of list.
        '''
        alignment_string = re.sub(r"'s", r" 's", alignment_string)

        group = [l.split() for l in re.split(r"\]\s*\[", re.search(r'\[(.*)\]', alignment_string).group(1))]
        return group

    def extract(self, fpath, apath):
        def copy_gram(global_gram, local_gram):
            for k in local_gram:
                global_gram[k].update(local_gram[k])

        #print fpath
        with open(apath) as afile:
            align_syn = self._read_alignment(afile.readline())
            align_sem = afile.read()
            (relation, instance) = self._read_semalign(align_sem)
            #print relation
            #print instance
            annotated_tree = self._annotate(fpath, align_syn)
            instance = [i for i in instance if len(i) > 3]
            relation = [r for r in relation if len(r) > 3]
            extracted_tree = None
            try:
                extracted_tree = self._extract(annotated_tree)
                lgram = self._sem_align(extracted_tree, align_syn, relation, instance)
            except AssertionError, e:
                print "there is parsing error in {0}".format(fpath)
            except ValueError, e1:
                print "there is parsing error in {0}".format(fpath)
            except KeyError, e2:
                print "there is parsing error in {0}".format(fpath)
            else:
                print "Succeed to process in {0}".format(fpath)
                #copy the extracted tree to global grammar
                copy_gram(self.gram, lgram)

            if extracted_tree is not None:
                return [i for j in extracted_tree.values() for i in j]

    def _sem_align(self, extracted_tree, align_syn, relation, instance):
        '''
        align the semantics to the extracted grammar
        '''
        def transverse(tree):
            #find all the wholes in the tree, works a generator
            if tree is not None and type(tree) != str:
                #remove the group information, it's not useful anymore
                yield tree
                for child in tree:
                    for x in transverse(child):
                        yield x

        def find_hole(tree):
            for t in transverse(tree):
                #if t.node.has_key('group'):
                #    tree.node.pop('group')
                if t.node.has_key('cand'):
                    yield t

        def freeze(tree):
            #freeze featsruct
            if type(tree) is str:
                return tree
            else:
                for t in transverse(tree):
                    t.node.freeze()
                return tree.freeze()

        def treedeepcopy(tree):
            #there is a bug in nltk ParentedTree.copy(deep=True)
            #the node is not copied
            newtree = tree.copy(deep=True)
            for t in transverse(newtree):
                t.node = deepcopy(t.node)
            return newtree

        gram = defaultdict(set)

        instancedict = defaultdict(set)
        for i in instance:
            instancedict[i[0]].add(i[3])
        instance_index_set = set([i[3] for i in instance])
        relation_index_set = set([r[3] for r in relation])
        extree_index_set = set(extracted_tree.keys())
        unannotated = extree_index_set.difference(instance_index_set).difference(relation_index_set)
        # some tree is not even mentioned in the semantics alignment
        # one workaround is to compare the group with other groups
        # to amend the annotation
        alignhash = defaultdict()
        for l in align_syn:
            k,v ='_'.join(l[1:]), int(l[0])
            if v not in unannotated:
                alignhash[k] = v
            else:
                sim = alignhash[k]
                for key in instancedict:
                    if sim in instancedict[key]:
                        instancedict[key].add(v)

        # first deal with the instances
        for i in instance:
            index = i[3]
            # some instances reference to the same group with some relation,
            # delay it to procedure of relations
            if index in instance_index_set.difference(relation_index_set):
                etree = extracted_tree[index] #keep in mind itree is a list
                assert len(etree) == 1, "itree lengh larger than 1"
                itree = treedeepcopy(etree[0])
                #print i[2]
                for it in itree:
                    for t in transverse(it):
                        t.node.pop('group')
                    #make it hashable
                    fit = freeze(it)
                    assert hash(fit)
                    #put it into grammar
                    gram[i[2]].add(fit)
        # deal with the realtions
        for r in relation:
            index = r[3]
            etree = extracted_tree[index]
            assert len(etree) == 1, "There are more than one tree corresponding to one relation"
            itree = treedeepcopy(etree[0])
            #import ipdb; ipdb.set_trace()
            arg0 = r[0]
            arg1 = r[2]
            #print arg0, instancedict[r[0]]
            #print arg1, instancedict[r[2]]
            for t in find_hole(itree):
                #check all of the hole
                if not instancedict[arg0].isdisjoint(t.node['cand']):
                    t.node['sem'] = 0
                elif not instancedict[arg1].isdisjoint(t.node['cand']):
                    t.node['sem'] = 1
                #assert t.node.has_key('sem'), "failed to find the semantic anchor for current node"
                t.node.pop('cand')
            if itree.node.has_key('group'):
                for t in transverse(itree):
                    t.node.pop('group')
                    t.node.freeze()
            #put it into grammar
            fit = freeze(itree)
            assert hash(fit)
            gram[r[1]].add(fit)

        # return gram extracted from currentfile
        return gram

        #for trees in extracted_tree.values():
        #    for t in trees:
        #        t.draw()


    def _get_group(self, grammar_tree):
        group =  grammar_tree.node['group']
        assert len(group) == 1, "Tree is related to more than 1 index"
        return list(group)[0]

    def _read_semalign(self, align_str):
        '''
        read in semantic alignment information
        '''
        align =  sexprparse.parse_sexp(align_str)
        return (align[2], align[4])

    def _extract(self, annotated_tree):
        '''
        read in annotated tree, extract etree.
        input: annotated tree
        ouput: etrees
        '''
        #initialize the agenda
        agenda =  deque()
        agenda.append(annotated_tree)

        extracted_tree = defaultdict(list)

        #loop until agenda is empty
        while agenda:
            #import ipdb
            #ipdb.set_trace()
            currenttree = agenda.popleft()
            if self._is_wellformed(currenttree):
                # we've found a nice tree which can be added to the grammar! cool!
                #print "found good tree"
                #currenttree.draw()
                extracted_tree[self._get_group(currenttree)].append(currenttree)
            else:
                self._detect_conj(currenttree, agenda, extracted_tree)
                if self._detect_adjunct(currenttree, currenttree, agenda, extracted_tree):
                    continue
                self._detect_subs(currenttree, agenda, extracted_tree)
            #TEST

        return extracted_tree

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
            if self._detect_adjunct_help(annotated_tree, root, agenda, extracted_tree) is True:
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
        #print annotated_tree
        leftmost = annotated_tree[0]
        rightmost = annotated_tree[-1]
        leftgo = not isinstance(leftmost, str) and leftmost.height() > 1
        rightgo = not isinstance(rightmost, str) and rightmost.height() > 1
        while  leftgo or rightgo:
            if leftgo:
                if leftmost.node[Feature('type')] == pos and leftmost.node.get('head') is True:
                    # candidate adjuction node
                    if self._is_well_partitioned(annotated_tree, leftmost):
                        # it's really adjuction node
                        # 1. deepcopy it and add substitute to the root
                        # 2. deepcopy the whole tree, replace found node as a adjuct hole
                        isadjunct = True

                        holetree = leftmost.copy(deep=True)
                        newadjunctwhole = ParentedTree(deepcopy(holetree.node), [])
                        newadjunctwhole.node['adj'] = True
                        #print "changing the hole group information"
                        #print newadjunctwhole.node['group']
                        newadjunctwhole.node['cand'] = newadjunctwhole.node['group']
                        newadjunctwhole.node['group'] = set()
                        leftmost.parent()[leftmost.parent_index()] = newadjunctwhole
                        # copy the adjuct tree
                        adjuncttree = annotated_tree.copy(deep=True)
                        adjuncttree.node['adj'] = True
                        # when the adjuction is not at the root, subsitute the whole in
                        if not annotated_tree is root:
                            #print "find different"
                            annotated_tree.parent()[annotated_tree.parent_index()] = holetree
                            # put root tree in the agenda
                            self._grouping_help(root)
                            agenda.append(root)
                        # put new adjucttree in the agenda
                        self._grouping_help(adjuncttree)
                        #print "adding adjucttree"
                        #adjuncttree.draw()
                        agenda.append(adjuncttree)
                        self._grouping_help(holetree)
                        #print "adding holetree"
                        #holetree.draw()
                        agenda.append(holetree)
                        break
                leftmost = leftmost[0]
                leftgo = not isinstance(leftmost, str) and leftmost.height() > 1
            if rightgo:
                if rightmost.node[Feature('type')] == pos and rightmost.node.get('head') is True:
                    if self._is_well_partitioned(annotated_tree, rightmost):
                        isadjunct = True
                        holetree = rightmost.copy(deep=True)
                        newadjunctwhole = ParentedTree(deepcopy(holetree.node), [])
                        newadjunctwhole.node['adj'] = True
                        #print "changing the hole group information"
                        #print newadjunctwhole.node['group']
                        newadjunctwhole.node['cand'] = newadjunctwhole.node['group']
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
        while rightsib is not None:
            othergroup.update(rightsib.node['group'])
            rightsib = rightsib.right_sibling()
        while leftsib is not None:
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
        extracted_tree[self._get_group(annotated_tree)].append(annotated_tree)

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
                #print "changing the hole group information"
                #print subs_tree.node['group']
                subs_tree.node['cand'] = subs_tree.node['group']
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
                #print "changing the hole group information"
                #print subs_conjtree.node['group']
                subs_conjtree.node['cand'] = subs_conjtree.node['group']
                subs_conjtree.node['group'] = set()
                root[annotated_tree.treeposition()] = subs_conjtree

                # deal with conjtree
                for i in range(len(conjtree)):
                    if not (conjtree[i][0] == ',' or conjtree[i].node[Feature('type')] == 'CC'):
                        # needs to be substitued
                        agenda.append(conjtree[i].copy(deep=True))
                        subs_tree = ParentedTree(deepcopy(conjtree[i].node), [])
                        subs_tree.node['subs'] = True
                        #print "changing the hole group information"
                        #print newadjunctwhole.node['group']
                        subs_conjtree.node['cand'] = subs_conjtree.node['group']
                        subs_conjtree.node['group'] = set()
                        subs_tree.node['group'] = set()
                        conjtree[i] = subs_tree
                #update the grouping information of conjtree
                self._grouping_help(conjtree)
                extracted_tree[self._get_group(conjtree)].append(conjtree)
            else:
                for i in range(len(annotated_tree)):
                    self._detect_conj_help(annotated_tree[i], root, agenda, extracted_tree)


    def _is_conj_tree(self, annotated_tree):
        if annotated_tree.node[Feature('type')] == 'NP': # we can only deal with conjuction which happens in NP
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
                if(annotated_tree[i].node.get('head') is True):
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
            if find is False:
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
    import sys
    argparser = argparse.ArgumentParser()
    # to validate the input is a valid readable dir
    def readable_dir(prospective_dir):
        if not os.path.isdir(prospective_dir):
            raise Exception("readable_dir:{0} is not a valid path".format(prospective_dir))
        if os.access(prospective_dir, os.R_OK):
            return prospective_dir
        else:
            raise Exception("readable_dir:{0} is not a readable dir".format(prospective_dir))
    argparser.add_argument("corpus", type=readable_dir, help="corpus path which should be a directroy")
    argparser.add_argument("alignment", type=readable_dir, help="alignment path which should be a directory")
    argparser.add_argument("outfile", nargs='?', default=sys.stdout, type=argparse.FileType('w'), help="outputfile for extracted grammar")
    argparser.add_argument("--verbose", default="", help="output raw gammar extracted for each sentence. This parameter should be a directory")
    args = argparser.parse_args()
    # TODO: the whole logic needs to be rewritten
    if args.verbose:
        grammar_dir = args.verbose
    ltge = LtagExtractor()
    grammar_dir = "grammar"
    for root, dirs, files in os.walk(args.corpus):
        for f in files:
            #print f
            #TODO the directory is not pure, otherwise it doesn't require this step
            m = re.match(r'(.*?)\.pst-heads-fixed', f)
            if m:
                fpath = os.path.join(args.corpus, m.group())
                alpath = os.path.join(args.alignment, m.group(1)+'.ali')
                #grammar_dir = dpath + r'grammar/'
                if not os.path.exists(grammar_dir):
                    os.makedirs(grammar_dir)
                with open(os.path.join(grammar_dir, m.group(1) + r'.grm'), 'w') as grammarfile:
                    gram = ltge.extract(fpath, alpath)
                    if gram is not None:
                        for g in gram:
                            #g.draw()
                            grammarfile.write(g.pprint() + '\n')
                            grammarfile.write('\n')

    #ouput the grammar extracted
    ltge.output_gram(args.outfile)


if __name__ == '__main__':
    main()
