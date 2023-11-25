#!/bin/bash

# Load .bashrc, which loads: ~/.{bash_prompt,aliases,functions,path,dockerfunc,extra,exports}
if [[ -r "${HOME}/.bashrc" ]]; then
	# shellcheck source=/dev/null
	source "${HOME}/.bashrc"
fi

# Start keychain - only add each passphrase once after reboot
# --clear -> passphrases must be re-entered on login, but cron jobs will still have access to the unencrypted keys after the user logs out
eval "$(keychain --quiet --eval --agents ssh)"
