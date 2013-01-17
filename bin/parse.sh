#!/usr/bin/env bash

SD=`dirname $0`

mkdir -p $2

java -mx150m -cp "$SD/../utilities/stanford-parser-2012-07-09/*:" \
  edu.stanford.nlp.parser.lexparser.LexicalizedParser \
  -outputFormat "penn" \
  -outputFormatOptions "markHeadNodes" \
  -writeOutputFiles \
  -outputFilesDirectory $2 \
  edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz \
  $1/*.sent

for f in $2/*.sent.stp; do\
  mv $f $2/`basename $f .sent.stp`.pst-heads
done
