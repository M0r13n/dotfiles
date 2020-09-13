#!/bin/bash
# NOTE: This uses Linux-Brew and needs to be executed AFTER Linux-Brew was set up
# shellcheck disable=SC1091
cd "$(dirname "${BASH_SOURCE[0]}")" && . "./utils.sh" 

execute "brew install exa" "Installing Exa"
