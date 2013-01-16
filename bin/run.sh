#!/bin/sh

function pause(){
   read -p "$*"
}

echo "Run this script will overwrite the content in ouput directory! Are you sure to continue?"
pause 'Press [Enter] key to continue...'

#TODO

python extract/extractor.py ../output/fixed/ ../input/alignments/ ../output/final.gram --verbose ../output/grammar-verbose/ 
