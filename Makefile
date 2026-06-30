# Homelab control — thin wrappers around the commands we actually use.
# Run from the repo root, e.g. `make deploy`, `make check`, `make help`.

# Ansible lives in configure/. This repo sits on a WSL /mnt/c mount (world-
# writable), so Ansible ignores ansible.cfg unless we point at it explicitly.
ANSIBLE_DIR := configure
CFG         := ANSIBLE_CONFIG=$(CURDIR)/$(ANSIBLE_DIR)/ansible.cfg

# Which node(s) to act on. Override: `make deploy LIMIT=compute` or LIMIT=all
LIMIT ?= edge

.DEFAULT_GOAL := help
.PHONY: help deps deploy deploy-first check syntax ping edit

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

deps: ## Install Ansible collections from requirements.yml
	cd $(ANSIBLE_DIR) && $(CFG) ansible-galaxy collection install -r requirements.yml

deploy: ## Converge the lab (default LIMIT=edge)
	cd $(ANSIBLE_DIR) && $(CFG) ansible-playbook site.yml --limit $(LIMIT)

deploy-first: ## First run on a fresh node — prompts once for the sudo password
	cd $(ANSIBLE_DIR) && $(CFG) ansible-playbook site.yml --limit $(LIMIT) -K

check: ## Dry-run: show what would change, change nothing
	cd $(ANSIBLE_DIR) && $(CFG) ansible-playbook site.yml --limit $(LIMIT) --check --diff

syntax: ## Validate the playbook/roles parse
	cd $(ANSIBLE_DIR) && $(CFG) ansible-playbook site.yml --syntax-check

ping: ## Check Ansible can reach the node(s)
	cd $(ANSIBLE_DIR) && $(CFG) ansible $(LIMIT) -m ping

edit: ## Edit a SOPS secret: make edit FILE=secrets/edge-caddy.sops.env
	@test -n "$(FILE)" || { echo "Usage: make edit FILE=secrets/<name>.sops.env"; exit 1; }
	sops edit $(FILE)
