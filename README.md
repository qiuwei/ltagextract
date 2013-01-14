ltagextract
===========

extract lexicalized tree adjoin grammar from treebank


### Introduction
This project intends to extract Tree Adjoin Grammar with semantics aligned from KBGen corpus.

### Software depends
* clojure http://clojurhttp://nlp.stanford.edu/software/lex-parser.shtmle.org/
* python 2.7 http://www.python.org/download/releases/2.7/
* Java http://www.java.com/en/download/index.jsp
* NLTK NLTK is a leading platform for building Python programs to work with human language data. http://nltk.org/
* Stanford parser: . http://nlp.stanford.edu/software/lex-parser.shtml

### Howto
To reproduce our current result, a pipeline needs to be followed:
1. parse sentences using Stanford parser. We use the unlexicalized parser with head information output.
2. Deal with the conjunction occurred in the syntactic tree.
3. Normalize the syntactic tree gotten from step 2.
4. Extract TAG from the output of step 3
5. Assign semantics to the output of step 4

#### Step 1
To parse the corpus use Stanford parser, run
```bash
TODO
```

#### Step 2
To deal with the conjunctions, run
```bash
TODO`
```

#### Step 3
To Normalize the syntactic tree, run
```bash
TODO
```

#### Step 4&5:
To extract the TAG with semantics aligned, run
```bash
python2 extractor.py -h
usage: extractor.py [-h] [--verbose VERBOSE] corpus alignment [outfile]

positional arguments:
  corpus             corpus path which should be a directroy
  alignment          alignment path which should be a directory
  outfile            outputfile for extracted grammar

optional arguments:
  -h, --help         show this help message and exit
  --verbose VERBOSE  output raw gammar extracted for each sentence. This
                     parameter should be a directory
```
to check the help.


#### Other
We also provide a small tool to help you visualize TAG extracted from step 4 or step 5, run
```
python2 grammarviewer.py -h
usage: grammarviewer.py [-h] [filename]

Draw the tree according to grammar file

positional arguments:
  filename    The name of grammar file, stdin will be used if left open

optional arguments:
  -h, --help  show this help message and exit
```
As a side product, our package provides a s-expression parser for python. You may want to use it to reconstruct ParentedTree(NLTK) from the plain text representation of TAG.
```
