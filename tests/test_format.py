import xml.sax
from typing import Optional

import requests
from pytest import raises
from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax
from schema_salad.exceptions import ValidationException
from schema_salad.fetcher import DefaultFetcher

from cwl_utils.format import check_format


def _create_file(format_: Optional[str] = None):
    obj = {
        "class": "File",
        "basename": "example.txt",
        "size": 23,
        "contents": "hoopla",
        "nameroot": "example",
        "nameext": "txt",
    }
    if format_:
        obj["format"] = format_
    return obj


def _load_format(fetchurl: str):
    fetcher = DefaultFetcher({}, requests.Session())
    content = fetcher.fetch_text(fetchurl)
    graph = Graph()
    for fmt in ["xml", "turtle", "rdfa"]:
        try:
            graph.parse(data=content, format=fmt, publicID=str(fetchurl))
            break
        except (xml.sax.SAXParseException, TypeError, BadSyntax):
            pass
    return graph


def test_check_format():
    check_format(
        actual_file=_create_file(format_="http://edamontology.org/format_2330"),
        input_formats="http://edamontology.org/format_2330",
        ontology=_load_format("http://edamontology.org/EDAM.owl"),
    )


def test_check_format_no_format():
    with raises(ValidationException, match=r"File has no 'format' defined: .*"):
        check_format(
            actual_file=_create_file(),
            input_formats="http://edamontology.org/format_2330",
            ontology=_load_format("http://edamontology.org/EDAM.owl"),
        )


def test_check_format_no_input_formats():
    with raises(ValidationException, match=r"File has an incompatible format: .*"):
        check_format(
            actual_file=_create_file(format_="http://edamontology.org/format_2330"),
            input_formats=[],
            ontology=Graph(),
        )


def test_check_format_no_ontology():
    check_format(
        actual_file=_create_file(format_="http://edamontology.org/format_2330"),
        input_formats="http://edamontology.org/format_2330",
        ontology=Graph(),
    )
