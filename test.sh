#!/bin/bash
set -e
set -o pipefail

# execute makefile
if make full; then
	echo "No errors, hooray"
else
    sleep 0.5
	echo "Make failed :-("
	exit 1
fi
