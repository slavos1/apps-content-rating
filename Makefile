VENV ?= .venv
SHELL = bash
MODULE = check_rating
# INPUT_FILE = myapps.md
INPUT_FILE = myapps_20231012.md
# INPUT_FILE = small.md
DAT_FILE = ratings.dat
ADOC_FILE = ratings.adoc
PDF_FILE = ratings.pdf
HTML_FILE = ratings.html
PY_FILES = ${MODULE}/ tests/

all: get report

fmt:
	black -l100 ${PY_FILES}
	ruff --select E,F,I --fix --line-length 100 ${PY_FILES}

${INPUT_FILE}: ;

get gather: ${DAT_FILE}

${DAT_FILE}:: ${INPUT_FILE}
	${VENV}/bin/python -m ${MODULE} -d -i $< -o $@.tmp gather ${EXTRA}
	mv $@.tmp $@

report: ${HTML_FILE} ${PDF_FILE}

${ADOC_FILE}:: ${DAT_FILE}
#	${VENV}/bin/python ${MODULE}.py -n 2 -i "Parental Guidance" General 'Rated 3+' -- $< $@.tmp
#	${VENV}/bin/python ${MODULE}.py -n 30 -i "Rated for 3+" General -- $< $@.tmp
#	${VENV}/bin/python ${MODULE}.py -i "Rated for 3+" General -- $< $@.tmp
	${VENV}/bin/python -m ${MODULE} -d -i $< -o $@.tmp report -x "Rated for 3+" General ${EXTRA}
#	${VENV}/bin/python -m ${MODULE} -d -i $< -o $@.tmp report ${EXTRA}
	mv $@.tmp $@

${HTML_FILE}: ${ADOC_FILE}
	asciidoctor -o $@ $<

${PDF_FILE}: ${ADOC_FILE}
	asciidoctor-pdf -o $@ $<

help:
	${VENV}/bin/python -m ${MODULE} --help

clean_get:
	rm -rf ${DAT_FILE}

clean_report:
	rm -rf  ${ADOC_FILE} ${HTML_FILE} ${PDF_FILE}

clean: clean_get clean_report

rebuild: clean get report

test:
	PYTHONPATH=. ${VENV}/bin/pytest -vv --html=report.html --log-level=DEBUG --show-capture=all tests/ ${EXTRA}
