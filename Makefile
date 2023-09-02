# This file is part of cwl-utils,
# https://github.com/common-workflow-language/cwl-utils/, and is
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contact: common-workflow-language@googlegroups.com

# make format to fix most python formatting errors
# make pylint to check Python code for enhanced compliance including naming
#  and documentation
# make coverage-report to check coverage of the python scripts by the tests

MODULE=cwl_utils
PACKAGE=cwl-utils
EXTRAS=

# `SHELL=bash` doesn't work for some, so don't use BASH-isms like
# `[[` conditional expressions.
PYSOURCES=$(filter-out $(MODULE)/parser/cwl_v%,$(shell find $(MODULE) -name "*.py")) \
	  $(wildcard tests/*.py) create_cwl_from_objects.py load_cwl_by_path.py \
	  setup.py ${MODULE}/parser/cwl_v1_?_utils.py docs/conf.py
DEVPKGS=diff_cover  pylint pep257 pydocstyle flake8 tox tox-pyenv \
	isort wheel autoflake pyupgrade bandit auto-walrus \
	-rlint-requirements.txt -rtest-requirements.txt -rmypy-requirements.txt
DEBDEVPKGS=pep8 python-autopep8 pylint python-coverage pydocstyle sloccount \
	   python-flake8 python-mock shellcheck
VERSION=v$(shell echo $$(tail -n 1 cwl_utils/__meta__.py | awk '{print $$3}'))
mkfile_dir := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
UNAME_S=$(shell uname -s)

## all                    : default task (install cwl-utils in dev mode)
all: dev

## help                   : print this help message and exit
help: Makefile
	@sed -n 's/^##//p' $<

## cleanup                : shortcut for "make sort_imports format flake8 diff_pydocstyle_report"
cleanup: sort_imports format flake8 diff_pydocstyle_report

## install-dep            : install most of the development dependencies via pip
install-dep: install-dependencies

install-dependencies:
	pip install --upgrade $(DEVPKGS)
	pip install -r requirements.txt -r mypy-requirements.txt -r docs/requirements.txt

## install-deb-dep        : install many of the dev dependencies via apt-get
install-deb-dep:
	sudo apt-get install $(DEBDEVPKGS)

## install                : install the cwl-utils package and the scripts
install: FORCE
	pip install .$(EXTRAS)

## dev                    : install the cwl-utils package in dev mode
dev: install-dep
	pip install -e .$(EXTRAS)

## dist                   : create a module package for distribution
dist: dist/${MODULE}-$(VERSION).tar.gz

dist/${MODULE}-$(VERSION).tar.gz: $(SOURCES)
	python setup.py sdist bdist_wheel

## docs                   : make the docs
docs: FORCE
	cd docs && $(MAKE) html

## clean                  : clean up all temporary / machine-generated files
clean: FORCE
	rm -f ${MODULE}/*.pyc tests/*.pyc
	python setup.py clean --all || true
	rm -Rf .coverage
	rm -f diff-cover.html

# Linting and code style related targets
## sort_import            : sorting imports using isort: https://github.com/timothycrosley/isort
sort_imports: $(PYSOURCES)
	isort $^

remove_unused_imports: $(PYSOURCES)
	autoflake --in-place --remove-all-unused-imports $^

pep257: pydocstyle
## pydocstyle             : check Python docstring style
pydocstyle: $(PYSOURCES)
	pydocstyle --add-ignore=D100,D101,D102,D103 $^ || true

pydocstyle_report.txt: $(PYSOURCES)
	pydocstyle setup.py $^ > $@ 2>&1 || true

## diff_pydocstyle_report : check Python docstring style for changed files only
diff_pydocstyle_report: pydocstyle_report.txt
	diff-quality --compare-branch=main --violations=pydocstyle --fail-under=100 $^

## codespell              : check for common misspellings
codespell:
	codespell -w $(shell git ls-files | grep -v mypy-stubs)

## format                 : check/fix all code indentation and formatting (runs black)
format: $(PYSOURCES) FORCE
	black $(PYSOURCES)

format-check: $(PYSOURCES)
	black --diff --check $^

## pylint                 : run static code analysis on Python code
pylint: $(PYSOURCES)
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
                $^ -j0|| true

pylint_report.txt: $(PYSOURCES)
	pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" \
		$^ -j0> $@ || true

diff_pylint_report: pylint_report.txt
	diff-quality --compare-branch=main --violations=pylint pylint_report.txt

.coverage: testcov

coverage: .coverage
	coverage report

coverage.xml: .coverage
	coverage xml

coverage.html: htmlcov/index.html

htmlcov/index.html: .coverage
	coverage html
	@echo Test coverage of the Python code is now in htmlcov/index.html

coverage-report: .coverage
	coverage report

diff-cover: coverage.xml
	diff-cover --compare-branch=main $^

diff-cover.html: coverage.xml
	diff-cover --compare-branch=main $^ --html-report $@

## test                   : run the cwl-utils test suite
test: $(PYSOURCES)
	python -m pytest -rsx ${PYTEST_EXTRA}

## testcov                : run the cwl-utils test suite and collect coverage
testcov: $(PYSOURCES)
	pytest --cov ${PYTEST_EXTRA}

sloccount.sc: $(PYSOURCES) Makefile
	sloccount --duplicates --wide --details $^ > $@

## sloccount              : count lines of code
sloccount: $(PYSOURCES) Makefile
	sloccount $^

list-author-emails:
	@echo 'name, E-Mail Address'
	@git log --format='%aN,%aE' | sort -u | grep -v 'root'

mypy3: mypy
mypy: $(filter-out setup.py,${PYSOURCES})
	MYPYPATH=$$MYPYPATH:mypy-stubs mypy $^

shellcheck: FORCE
	shellcheck release-test.sh

pyupgrade: $(PYSOURCES)
	pyupgrade --exit-zero-even-if-changed --py38-plus $^
	auto-walrus $^

release-test: FORCE
	git diff-index --quiet HEAD -- || ( echo You have uncommitted changes, please commit them and try again; false )
	./release-test.sh

release: release-test
	. testenv2/bin/activate && \
		python testenv2/src/${PACKAGE}/setup.py sdist bdist_wheel
	. testenv2/bin/activate && \
		pip install twine && \
		twine upload testenv2/src/${PACKAGE}/dist/* && \
		git tag ${VERSION} && git push --tags

flake8: $(PYSOURCES)
	flake8 $^

cwl_utils/parser/cwl_v1_0.py: FORCE
	schema-salad-tool --codegen python \
		--codegen-parser-info "org.w3id.cwl.v1_0" \
		https://github.com/common-workflow-language/common-workflow-language/raw/codegen/v1.0/CommonWorkflowLanguage.yml \
		> $@

cwl_utils/parser/cwl_v1_1.py: FORCE
	schema-salad-tool --codegen python \
		--codegen-parser-info "org.w3id.cwl.v1_1" \
		https://github.com/common-workflow-language/cwl-v1.1/raw/codegen/CommonWorkflowLanguage.yml \
		> $@

cwl_utils/parser/cwl_v1_2.py: FORCE
	schema-salad-tool --codegen python \
		--codegen-parser-info "org.w3id.cwl.v1_2" \
		https://github.com/common-workflow-language/cwl-v1.2/raw/1.2.1_proposed/CommonWorkflowLanguage.yml \
		> $@

regen_parsers: cwl_utils/parser/cwl_v1_*.py

FORCE:

# Use this to print the value of a Makefile variable
# Example `make print-VERSION`
# From https://www.cmcrossroads.com/article/printing-value-makefile-variable
print-%  : ; @echo $* = $($*)
