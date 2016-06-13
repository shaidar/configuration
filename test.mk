
yml_files:=$(shell find . -name "*.yml")
json_files:=$(shell find . -name "*.json")
images = $(shell git diff --name-only $(TRAVIS_COMMIT_RANGE) | python util/parsefiles.py)

test: test.syntax test.edx_east_roles

test.syntax: test.syntax.yml test.syntax.json test.syntax.dockerfiles

test.syntax.yml: $(patsubst %,test.syntax.yml/%,$(yml_files))

test.syntax.yml/%:
	python -c "import sys,yaml; yaml.load(open(sys.argv[1]))" $* >/dev/null

test.syntax.json: $(patsubst %,test.syntax.json/%,$(json_files))

test.syntax.json/%:
	jsonlint -v $*

test.syntax.dockerfiles:
	python util/check_dockerfile_coverage.py "$(images)"
	
test.edx_east_roles:
	tests/test_edx_east_roles.sh
