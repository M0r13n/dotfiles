SHELL := bash

.PHONY: all
all: bin usr dotfiles etc ## Installs the bin and etc directory files and the dotfiles.

.PHONY: full
full: all programs

.PHONY: bin
bin: ## Installs the bin directory files.
	# add aliases for things in bin
	for file in $(shell find $(CURDIR)/bin -type f -not -name "*-backlight" -not -name ".*.swp"); do \
		f=$$(basename $$file); \
		sudo ln -sf $$file /usr/local/bin/$$f; \
	done

.PHONY: dotfiles
dotfiles: ## Installs the dotfiles.
	# add aliases for dotfiles
	for file in $(shell find $(CURDIR) -name ".*" -not -name ".gitignore" -not -name ".git" -not -name ".config" -not -name ".github" -not -name ".*.swp" -not -name ".gnupg"); do \
		f=$$(basename $$file); \
		ln -sfn $$file $(HOME)/$$f; \
	done; \
	
	# add global gitignore
	ln -s -f $(CURDIR)/gitignore $(HOME)/.gitignore;

	# add global gitconf
	ln -s -f $(CURDIR)/gitconfig $(HOME)/.gitconfig;

	# make .config dir
	mkdir -p $(HOME)/.config;
	# symlink bash_profile
	ln -sf $(CURDIR)/.bash_profile $(HOME)/.profile;
	


.PHONY: etc
etc: ## Installs the etc directory files.
	# sudo mkdir -p /etc/docker/seccomp
	for file in $(shell find $(CURDIR)/etc -type f -not -name ".*.swp"); do \
		f=$$(echo $$file | sed -e 's|$(CURDIR)||'); \
		sudo mkdir -p $$(dirname $$f); \
		sudo ln -s -f $$file $$f; \
	done

.PHONY: usr
usr: ## Installs the usr directory files.
	for file in $(shell find $(CURDIR)/usr -type f -not -name ".*.swp"); do \
		f=$$(echo $$file | sed -e 's|$(CURDIR)||'); \
		sudo mkdir -p $$(dirname $$f); \
		sudo ln -s -f $$file $$f; \
	done

.PHONY: test
test: shellcheck ## Runs all the tests on the files in the repository.


.PHONY: programs
programs: ## Installs default programs for ubuntu
	for file in $(shell find $(CURDIR)/ext -type f); do \
		chmod +x $$file; \
	done
	$(CURDIR)/ext/install.sh


# if this session isn't interactive, then we don't want to allocate a
# TTY, which would fail, but if it is interactive, we do want to attach
# so that the user can send e.g. ^C through.
INTERACTIVE := $(shell [ -t 0 ] && echo 1 || echo 0)
ifeq ($(INTERACTIVE), 1)
	DOCKER_FLAGS += -t
endif

.PHONY: shellcheck
shellcheck: ## Runs the shellcheck tests on the scripts.
	docker run --rm -i $(DOCKER_FLAGS) \
		--name df-shellcheck \
		-v $(CURDIR):/usr/src:ro \
		--workdir /usr/src \
		jess/shellcheck ./test.sh

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
