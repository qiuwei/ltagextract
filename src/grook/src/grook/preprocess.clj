(ns grook.preprocess
  (:refer-clojure :exclude [==])
  (:use clojure.core.logic
        [clojure.pprint :only [pprint]])
  (:require [clojure.walk :as walk]
            [clojure.java.io :as io])
  (:gen-class :main true))

;; Running this cleans any previously defined rules from the namespace.
(dorun (for [[sym var] (ns-interns *ns*)
             :when (::rule (meta var))]
         (ns-unmap *ns* sym)))

(def COMMA
  "The comma is not allowed as a symbol in Clojure code. Hence,
  to refer to the symbol, we have to write it down indirectly."
  (symbol ","))

(defn read-tree
  "Reads in the tree stored in the `file'."
  [file]
  (->> file
    slurp
    read-string
    ; Since the Clojure reader treats commas as whitespace, we put
    ; them back by replacing any instance of () with (, ,).
    (walk/postwalk #({() (list COMMA COMMA)} % %))))

(def ^:dynamic ^{:doc "Bind this Var to some value before calling
  fix-tree and records of all the adjunctions performed will
  be conjed onto it."} *fix-tree-adjunctions*)

(defn record-adjunct
  "Records an adjunction performed within fix-tree."
  [phrase adjunct]
  (if (thread-bound? #'*fix-tree-adjunctions*)
    (set! *fix-tree-adjunctions* (conj *fix-tree-adjunctions*
                                       {:phrase phrase
                                        :adjunct adjunct}))))

(defn has-more-thano
  "A goal satisfied iff l is a list with more than n elements; n is
  not a relational argument."
  [n l]
  (fresh [a d]
    (conso a d l)
    (if (pos? n)
      (has-more-thano (dec n) d)
      succeed)))

(defn poly-appendo
  "Like clojure.core.logic/appendo, but works with arbitrary number of
  args, like clojure.core/concat."
  ([x y]
     (== x y))
  ([x y & more]
     (fresh [z]
       (apply poly-appendo z more)
       (appendo x y z))))

(defn adjuncto
  "A goal satisfied iff `adjunct' is identified as an adjunct in the
  phrase `phrase' (for the more general case when the adjunct is a
  child of the constituent it modifies)."
  [phrase adjunct]
  (conde ; We treat all PPs as adjuncts.
         [(firsto adjunct 'PP)]
         [(firsto adjunct 'S)
          ; We don't want sentential complements such as "[to do Y]"
          ; in "The function of X is [to do Y]" to be recognized as
          ; adjuncts. Example file: ex03a.46
          (fresh [to _]
            (conda [(== adjunct ['S ['VP=H to _]])
                      (!= to ['TO=H 'to])]
                   [succeed]))]
         ; Commas are viewed as adjuncts. Usually, they introduce a
         ; sentential complement or a PP. Treating commas as just
         ; other adjuncts lets us extract both the comma and the
         ; adjunct it introduces as a two-level auxiliary tree.
         [(firsto adjunct COMMA)]
         [(firsto adjunct 'SBAR)
          ; We only want SBARS which correspond to appositive
          ; relative clauses introduced by the word "which".
          (fresh [_]
            (== adjunct ['SBAR ['WHNP=H ['WDT=H 'which]] _]))]))

(defn ^::rule fix-adjunctiono
  "A rule which takes a left-most or right-most child A, which is an
  adjunct, and puts the A on a separate level from the other children,
  i.e. (R A ...) -> (R A (R ...)) or (R ... A) -> (R (R ...) A).

  This solves the general case when modifiers and adjuncts end up as
  children of the consituent they modify (e.g. in VPs)."
  [in-tree out-tree]
  (fresh [root children other-children adjunct head-child]
    (conso root children in-tree)
    (has-more-thano 2 children)
    (conde [(conso adjunct other-children children)
            (== out-tree (list root adjunct head-child))]
           [(appendo other-children (list adjunct) children)
            (== out-tree (list root head-child adjunct))])
    (conso root other-children head-child)
    (adjuncto in-tree adjunct)
    ; Record the phrase-adjunct pair we have found.
    (project [in-tree adjunct]
      (do (record-adjunct in-tree adjunct)
        succeed))))

(defn ^::rule fix-flat-npo
  "A rule which takes an NP whose head is preceded by a modifier and
  puts the modifier and the head under a new binary head node. The
  head noun can be any noun or noun phrase which is either the last
  child of the NP or is followed by a comma or conjunction.
  I.e., (NP ... MOD (N ...) (COMMA|CONJ) ...) ->
        (NP ... (N MOD (N ...)) (COMMA|CONJ) ...)
  and (NP ... MOD (N ...)) -> (NP ... (N MOD (N ...))).

  This solves the case when modifiers are on the same level of the
  tree as the constituent they modify (only NPs in our data)."
  [in-np out-np]
  (fresh [root-tag prefix modifier modifier-tag head-noun head-noun-tag
          suffix affixes new-head]
    (membero root-tag '[NP NP=H])
    (poly-appendo [root-tag] prefix [modifier] [head-noun] suffix in-np)
    (appendo prefix suffix affixes)
    (!= affixes ())
    (firsto modifier modifier-tag)
    (membero modifier-tag ['NN 'NNP 'JJ 'VBN 'ADJP])
    (firsto head-noun head-noun-tag)
    (membero head-noun-tag ['NN=H 'NNP=H 'NNS=H 'NP=H])
    (conde [(emptyo suffix)]
           [(fresh [conjunction conjunction-tag]
              (firsto suffix conjunction)
              (firsto conjunction conjunction-tag)
              (membero conjunction-tag ['CC COMMA]))])
    (== new-head (list head-noun-tag modifier head-noun))
    (poly-appendo [root-tag] prefix [new-head] suffix out-np)
    ; Record the phrase-adjunct pair we have found.
    (project [in-np modifier]
      (do (record-adjunct in-np modifier)
        succeed))))

(defmacro transformo
  "Is satisfied when out-tree is a normalized version of the in-tree
  node. Tries to use any goal annotated with ::rule."
  [in-tree out-tree]
  `(conde ~@(for [[sym var] (ns-interns *ns*)
                  :when (::rule (meta var))]
              [(list sym in-tree out-tree)])))

(defn try-transform
  "Repeatedly transforms the input phrase tree until no further
  normalization can be found."
  [in-tree]
  (let [solutions (run 1 [out-tree]
                    (transformo in-tree out-tree))]
    (if (empty? solutions)
      in-tree
      (recur (first solutions)))))

(defn fix-tree
  "Walks the tree bottom-up and tries to normalize every phrase.
  If you bind a value to *fix-tree-adjunctions*, a record of every
  adjunction performed by the algorithm will be conjed onto it."
  [tree]
  (walk/prewalk try-transform tree))


(defn -main
  "Reads trees from input-dir/*.pst-heads files and writes their
  normalized versions to output-dir/*.pst-heads-fixed files."
  [input-dir output-dir]
  (dorun (for [file (file-seq (io/file input-dir))
               :let [name (.getName file)
                     out-file (io/file (str output-dir "/" name "-fixed"))]
               :when (.endsWith name ".pst-heads")]
           (do (.. out-file getParentFile mkdirs)
               (with-open [fixed-file (io/writer out-file)]
                 (pprint (fix-tree (read-tree file)) fixed-file))))))



;; What follows is code we used for playing with and examining the
;; dataset during development time.

(comment
  (def tree-dir
    "Directory containing the parse trees which should be processed."
    "../../output/parsed"))

(comment
  (def trees
    "Our dataset, represented as a map from file names to the trees
    contained within."
    (into {} (for [file (file-seq (io/file tree-dir))
                   :let [name (.getName file)]
                   :when (.endsWith name ".pst-heads")]
               [name (read-tree file)]))))

(comment
  (def fixed-trees
    "A map from tree filenames to their fixed versions."
    (into {} (for [[name tree] trees]
               [name (fix-tree tree)]))))

(comment
  (def adjunctions
  "A vector recording all the phrases which we recognized as
  adjunctions. This is the place to check for `false positives',
  occassions when we identified something as an adjunct even though it
  could have been something else."
    (apply concat (for [[name tree] trees]
                    (binding [*fix-tree-adjunctions* []]
                      (fix-tree tree)
                      (map #(assoc % :name name) *fix-tree-adjunctions*))))))

(comment
  (defn interesting-phrases
  "Selects phrases with more than two children from all the
  relevant-trees. relevant-trees is expected to be a map from tree
  names to trees. This is the place to check for false
  negatives (places where the system should have done more
  normalization)."
    [relevant-trees]
    (for [[name tree] relevant-trees
          subtree (tree-seq seq? seq tree)
          :when (and (seq? subtree)
                     (> (count subtree) 3)
                     (not= (last subtree) '(. .)))]
      [name subtree])))

(comment
  (def fixed-dir
    "The place where to save all the processed trees."
    "../../output/fixed/"))


(comment
  (defn fix-all-the-trees!
    "Reads in all the trees from tree-dir, processes them and saves the
  results in fixed-dir."
    []
    (-main tree-dir fixed-dir)))
