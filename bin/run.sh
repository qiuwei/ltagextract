#!/usr/bin/env bash

function pause(){
   read -p "$*"
}

echo "Running this script will overwrite the content in output directory! Are you sure to continue?"
pause 'Press [Enter] key to continue...'

SD=`dirname $0`

java -jar "$SD"/aggregation-0.1.1-SNAPSHOT-standalone.jar \
  "$SD"/../input/triples/ "$SD"/../output/aggregated/

"$SD"/parse.sh "$SD"/../input/sentences/ "$SD"/../output/parsed/

java -jar "$SD"/grook-0.1.0-SNAPSHOT-standalone.jar \
  "$SD"/../output/parsed/ "$SD"/../output/fixed/

PYTHONPATH="$SD/../utilities/nltk-2.0.4/:$PYTHONPATH" python2 "$SD"/extract/extractor.py \
  "$SD"/../output/fixed/ "$SD"/../input/alignments/ "$SD"/../output/final.gram \
   --verbose "$SD"/../output/grammar-verbose/

