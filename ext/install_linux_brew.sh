#!/bin/bash
# shellcheck disable=SC1091
cd "$(dirname "${BASH_SOURCE[0]}")" && . "./utils.sh" 
declare -r URL_BREW='https://raw.githubusercontent.com/Homebrew/install/master/install.sh'

install_brew(){
    /bin/bash -c "$(curl -fsSL $URL_BREW)" > /dev/null
}

if execute "install_brew" 'Installing brew'; then
    print_success "Installed Linux-Brew"
else
    print_error "Linux-Brew failed with $?"
    exit 1
fi
