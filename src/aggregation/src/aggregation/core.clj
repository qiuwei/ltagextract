(ns aggregation.core
  (:require [clojure.java.io :as io])
  (:gen-class :main true))

(defn read-kbgen-data
  "To read in the data, we can simply use the Clojure reader since we
  are dealing with Common Lisp data structures. We also turn the alist
  into a Clojure hashmap."
  [filename]
  (apply hash-map (drop 1 (read-string (slurp filename)))))

(defn render-kbgen-data
  "Here we painfully recreate the formatting of the original triple files."
  [data]
  (let [render-triples (fn [triples]
                         (apply str (interleave (repeat "\n            ")
                                                (map pr-str triples))))]
    (str "(KBGEN-INPUT\n"
         "    :TRIPLES ("
         (render-triples (:TRIPLES data))
         ")\n"
         "    :INSTANCE-TYPES ("
         (render-triples (:INSTANCE-TYPES data))
         ")\n"
         "    :ROOT-TYPES ("
         (render-triples (:ROOT-TYPES data))
         "))\n")))

(defn write-kbgen-data!
  "Writes the KBGen data to the specified file, preserving original formatting."
  [data file]
  (spit file (render-kbgen-data data)))

(defn gen-coord-var
  "Produces a new Coordination variable with its unique ID (respective
  to all the other Coordination variables generated by the same
  process)."
  []
  (symbol (str (gensym "|Coordination") "|")))

(defn coordinate-objects-list
  "OBSOLETE: replaced with coordinate-objects-flat
  Given a sequence of objects, produces a sequence of triples that
  represent a binary tree of coordinations which has the given objects
  as leafs. The output value is a pair of the generated triples and
  the name of the coordination which sits at the top of the tree.

  The nodes in the trees we produce always have at least one leaf
  child, so they resemble linked lists more than binary trees. This is
  a desired property, as it lets us align punctuation and conjunctions
  to the individual nodes of the tree."
  [objects]
  (reduce (fn [[coord-triples old-coord-root] object-to-add]
            (let [new-coord-root (gen-coord-var)]
              [(conj coord-triples
                     (list new-coord-root '|coordinates| old-coord-root)
                     (list new-coord-root '|coordinates| object-to-add))
               new-coord-root]))
          [[] (first objects)]
          (rest objects)))

(defn coordinate-objects-flat
  "Given a sequence of objects, produces a sequence of triples that
  accumulates all the objects under a coordination construct. The
  output value is a pair of the generated triples and the name of the
  coordination variable."
  [objects]
  (let [coord-root (gen-coord-var)]
    [(map (fn [object-to-add]
            (list coord-root '|coordinates| object-to-add))
          objects)
     coord-root]))

(defn coordinate-triples
  "Given a sequence of triples which share the same left-hand side
  object and relation, returns another sequence of triples which
  aggregates the shared right-hand side objects using coordination
  constructs."
  [related-triples]
  (let [[left-object relation _] (first related-triples)
        [coord-triples coord-root] (coordinate-objects-flat (map #(nth % 2)
                                                                 related-triples))]
    (conj coord-triples (list left-object relation coord-root))))

(defn aggregate-data
  "Given the KBGen data, returns a variation of the data which uses
  explicit coordination constructs instead of allowing more than one
  value per object and relation."
  [data]
  (update-in data [:TRIPLES]
             (fn [triples]
               (let [grouped-triples (group-by (partial take 2) triples)]
                 (apply concat (for [related-triples (vals grouped-triples)]
                                 (if (= 1 (count related-triples))
                                   related-triples
                                   (coordinate-triples related-triples))))))))

(defn -main
  "Performs the coordination aggregation on all input-dir/*.trip files
  and stores the results in output-dir/*.trip-agg files."
  [input-dir output-dir]
  (dorun (for [file (file-seq (io/file input-dir))
               :let [path (.getCanonicalPath file)
                     out-file (io/file (str output-dir "/" (.getName file) "-agg"))]
               :when (.endsWith path ".trip")]
           (do (.. out-file getParentFile mkdirs)
               (write-kbgen-data! (aggregate-data (read-kbgen-data path))
                                  out-file)))))
