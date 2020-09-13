#!/bin/bash

# Load .bashrc, which loads: ~/.{bash_prompt,aliases,functions,path,dockerfunc,extra,exports}
if [[ -r "${HOME}/.bashrc" ]]; then
	# shellcheck source=/dev/null
	source "${HOME}/.bashrc"
fi

# Rust
export PATH="$HOME/.cargo/bin:$PATH"

# Python
export  PATH="$HOME/.local/bin:$PATH"
