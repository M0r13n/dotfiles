#!/bin/bash
# shellcheck disable=SC1091

cd "$(dirname "${BASH_SOURCE[0]}")" && . "./utils.sh" 
declare -r URL_PIP="https://bootstrap.pypa.io/get-pip.py"
TMP_PIP_FILE="$(mktemp /tmp/XXXXX)"
declare -r TMP_PIP_FILE

install_package "Python 3" "python3"
install_package "Python 3 Disutils" "python3-distutils"
execute "curl ${URL_PIP} -q -o ${TMP_PIP_FILE} >/dev/null" "Download PIP"
execute "python3 ${TMP_PIP_FILE} --user" "Install PIP"
rm -rf "${TMP_PIP_FILE}"
