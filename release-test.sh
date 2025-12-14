#!/bin/bash

set -e
set -x

export LC_ALL=C

package=cwl-utils
module=cwl_utils
extras="[pretty,testing]"

if [ "$GITHUB_ACTIONS" = "true" ]; then
    # We are running as a GH Action
    repo=${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git
    HEAD=${GITHUB_REF}
else
    repo=https://github.com/common-workflow-language/cwl-utils.git
    HEAD=$(git rev-parse HEAD)
fi
run_tests="bin/py.test --pyargs ${module}"
pipver=23.1  # minimum required version of pip for Python 3.12
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

rm -Rf testenv? || /bin/true


if [ "${RELEASE_SKIP}" != "head" ]
then
	python3 -m venv testenv1
	# First we test the head
	# shellcheck source=/dev/null
	source testenv1/bin/activate
	pip install --force-reinstall -U pip==${pipver} build
	pip install ".${extras}"
	make test
	pip uninstall -y ${package} || true; pip uninstall -y ${package} || true; make install
	mkdir testenv1/not-${module}
	# if there is a subdir named '${module}' py.test will execute tests
	# there instead of the installed module's tests
	pushd testenv1/not-${module}
	# shellcheck disable=SC2086
	../${run_tests}; popd
fi

python3 -m venv testenv2
python3 -m venv testenv3
python3 -m venv testenv4
python3 -m venv testenv5
rm -Rf testenv[2345]/local

# Secondly we test via pip

pushd testenv2
# shellcheck source=/dev/null
source bin/activate
pip install --force-reinstall -U pip==${pipver} \
        && pip install build wheel
# The following can fail if you haven't pushed your commits to ${repo}
pip install -e "git+${repo}@${HEAD}#egg=${package}${extras}"
pushd src/${package}
pip install build
make dist
make test
cp dist/${module}*tar.gz ../../../testenv3/
cp dist/${module}*whl ../../../testenv4/
pip uninstall -y ${package} || true; pip uninstall -y ${package} || true; make install
popd # ../.. no subdir named ${proj} here, safe for py.testing the installed module
# shellcheck disable=SC2086
${run_tests}
popd

# Is the source distribution in testenv2 complete enough to build
# another functional distribution?

pushd testenv3/
# shellcheck source=/dev/null
source bin/activate
pip install --force-reinstall -U pip==${pipver} \
        && pip install build wheel
package_tar=$(find . -name "${module}*tar.gz")
pip install "${package_tar}${extras}"
mkdir out
tar --extract --directory=out -z -f ${module}*.tar.gz
pushd out/${module}*
make dist
make test
pip uninstall -y ${package} || true; pip uninstall -y ${package} || true; make install
mkdir ../not-${module}
pushd ../not-${module}
# shellcheck disable=SC2086
../../${run_tests}; popd
popd
popd

# Is the wheel in testenv2 installable and will it pass the tests

pushd testenv4/
# shellcheck source=/dev/null
source bin/activate \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install build wheel
pip install "$(ls ${module}*.whl)${extras}"
mkdir not-${module}
pushd not-${module}
# shellcheck disable=SC2086
../${run_tests}; popd
popd
