# grook

A small Clojure program to deflatten parse trees coming out of the
Stanford parser, making them more amenable to TAG extraction.

## Usage

To run, do one of the following:

lein run <input-dir> <output-dir>

java -jar <grook-jarfile> <input-dir> <output-dir>

<grook-jarfile> <input-dir> <output-dir> # the jarfile has to be executable


The <input-dir> should be a folder holding files with the .pst-heads
filename extension, whose contents should be phrase structure trees in
the Penn treebank format, with the head information annotated as by
the Stanford parser. The normalized parse trees will be stored in the
<output-dir>, in files with the .pst-heads-fixed filename extension.


## Compiling

To produce the executable jarfile that is used the bin directory, run
```lein uberjar```. The jarfile will be stored in
target/grook-0.1.0-SNAPSHOT-standalone.jar.

## License

Copyright © 2012 Jiri Marsik, Wei Qiu

Distributed under the Eclipse Public License, the same as Clojure.
