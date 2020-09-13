#!/bin/bash
# shellcheck disable=SC1091

cd "$(dirname "${BASH_SOURCE[0]}")" && . "./utils.sh" 
declare -r URL_PIP="https://bootstrap.pypa.io/get-pip.py"


install_package "Python 3" "python3"
execute "curl ${URL_PIP} -q -o get-pip.py >/dev/null" "Download PIP"
execute "python3 ./get-pip.py --user" "Install PIP"
rm get-pip.py
