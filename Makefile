# o2-scalpel — top-level Makefile
#
# Stage 1J target ``generate-plugins`` regenerates the entire boostvolt-style
# marketplace from the Stage 1E LanguageStrategy registry by running the
# o2-scalpel-newplugin CLI for each language plus the marketplace.json
# aggregator helper.
#
# Override OUT to write the trees somewhere other than the repo root, and
# LANGUAGES to limit the run (e.g. ``make generate-plugins LANGUAGES=rust``).

.PHONY: generate-plugins help

OUT ?= .
LANGUAGES ?= rust python

PYBIN := vendor/serena/.venv/bin

help:
	@echo "Targets:"
	@echo "  generate-plugins  Regenerate o2-scalpel-<lang>/ trees + marketplace.json"
	@echo ""
	@echo "Variables:"
	@echo "  OUT=$(OUT)             Output parent directory"
	@echo "  LANGUAGES='$(LANGUAGES)'  Languages to emit"

generate-plugins:
	@for lang in $(LANGUAGES); do \
	  $(PYBIN)/o2-scalpel-newplugin --language $$lang --out $(OUT) --force ; \
	done
	@$(PYBIN)/python -m serena.refactoring.cli_newplugin_marketplace --out $(OUT) $(LANGUAGES)
