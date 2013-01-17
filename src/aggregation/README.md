# aggregation

A simple Clojure program to aggregate objects in KBGen triples into
coordination structures. This makes it easier to align the resulting
triples to punctuation and conjunctions used in coordination.

## Usage

To run, do one of the following:

lein run <input-dir> <output-dir>

java -jar <aggregation-jarfile> <input-dir> <output-dir>

<aggregation-jarfile> <input-dir> <output-dir> # the jarfile has to be executable


The <input-dir> should be a folder holding files with the .trip
filename extension, whose contents should be the KBGEN-INPUT triple
sets. The resulting triples where coordination was reified will be
stored in the <output-dir>, in files with the .trip-agg filename
extension.

## Compiling

To produce the executable jarfile that is used the bin directory, run
```lein uberjar```. The jarfile will be stored in
target/aggregation-0.1.1-SNAPSHOT-standalone.jar.

## License

Copyright © 2012 Jiri Marsik, Wei Qiu

Distributed under the Eclipse Public License, the same as Clojure.
