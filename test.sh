#!/bin/bash
set -e
set -o pipefail

assert_installed(){
	declare -a -r progs=("python3" "curl" "batcat" "jq")
	for i in "${progs[@]}"
	do
		if ! which "$i" &>/dev/null; then
			echo "$i not installed"
			exit 1
		fi
	done
	echo "No errors, hooray"
}

# execute makefile
if make full; then
	assert_installed
else
    sleep 0.5
	echo "Make failed :-("
	exit 1
fi
