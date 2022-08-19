"""Tests of cwl_utils.file_formats."""

import xml.sax
from typing import Optional

import requests
from pytest import raises
from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax
from schema_salad.exceptions import ValidationException
from schema_salad.fetcher import DefaultFetcher

from cwl_utils.file_formats import check_format
from cwl_utils.types import CWLObjectType


def _create_file(format_: Optional[str] = None) -> CWLObjectType:
    obj: CWLObjectType = {
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


def _load_format(fetchurl: str) -> Graph:
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


def test_check_format() -> None:
    check_format(
        actual_file=_create_file(format_="http://edamontology.org/format_2330"),
        input_formats="http://edamontology.org/format_2330",
        ontology=_load_format("http://edamontology.org/EDAM.owl"),
    )


def test_check_format_subformat() -> None:
    """Test of check_format with a subformat."""
    check_format(
        actual_file=_create_file(format_="http://edamontology.org/format_1929"),
        input_formats="http://edamontology.org/format_2330",
        ontology=_load_format("http://edamontology.org/EDAM.owl"),
    )


def test_check_format_no_format() -> None:
    """Confirm that a missing format produces the expected exception."""
    with raises(ValidationException, match=r"File has no 'format' defined: .*"):
        check_format(
            actual_file=_create_file(),
            input_formats="http://edamontology.org/format_2330",
            ontology=_load_format("http://edamontology.org/EDAM.owl"),
        )


def test_check_format_no_ontology() -> None:
    """Confirm that precisely matching formats without an ontology still match."""
    check_format(
        actual_file=_create_file(format_="http://edamontology.org/format_2330"),
        input_formats="http://edamontology.org/format_2330",
        ontology=Graph(),
    )
