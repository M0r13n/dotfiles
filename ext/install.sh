#!/bin/bash

set -e
set -o pipefail

# shellcheck disable=SC1091
cd "$(dirname "${BASH_SOURCE[0]}")" && . "./utils.sh" 

# Update packges info first
execute "sudo apt update -y && sudo apt upgrade -y" "Updating Apt"

# Basic packages
install_package "cURL" "curl"
install_package "JQ: Command-line JSON processor" "jq"
install_package "BAT: A cat(1) clone with wings." "bat"
install_package "GCC" "gcc"
install_package "Bash Autocompletion" "bash-completion"

./install_linux_brew.sh
./install_python.sh
./install_exa.sh

