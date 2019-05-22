#!/usr/bin/env python
"""
Unpacks the result of `cwltool --unpack`.

Only tested with a single v1.0 workflow.
"""

import sys
import os
from typing import Text

from ruamel import yaml


def run(args):
    with open(args[0], "r") as source_handle:
        source = yaml.load(source_handle, yaml.SafeLoader)

    if '$graph' not in source:
        print("No $graph, so not for us.")
        return

    version = source.pop('cwlVersion')

    for entry in source['$graph']:
        entry_id = entry.pop("id")[1:]
        entry['cwlVersion'] = version
        imports = rewrite(entry, entry_id)
        if imports:
            for import_name in imports:
                rewrite_types(entry, "#{}".format(import_name), False)
        if entry_id == 'main':
            entry_id = "unpacked_{}".format(os.path.basename(args[0]))
        with open(entry_id, "w") as result_handle:
            yaml.dump(entry, result_handle, Dumper=yaml.SafeDumper)

def rewrite(document, doc_id):
    imports = set()
    if isinstance(document, list) and not isinstance(document, Text):
        for entry in document:
            imports.update(rewrite(entry, doc_id))
    elif isinstance(document, dict):
        this_id = document['id'] if 'id' in document else None
        for key, value in document.items():
            if key == 'run' and value[0] is '#':
                document[key] = value[1:]
            elif key in ('id', 'outputSource') and value.startswith('#' + doc_id):
                document[key] = value[len(doc_id)+2:]
            elif key == 'out':
                def rewrite_id(entry):
                    if entry['id'].startswith(this_id):
                        entry['id'] = entry['id'][len(this_id)+1:]
                    return entry
                document[key][:] = [rewrite_id(entry) for entry in value]
            elif key in ('source', 'scatter', 'items', "format"):
                if isinstance(value, Text) and value.startswith('#') and '/' in value:
                    referrant_file, sub = value[1:].split('/', 1)
                    if referrant_file == doc_id:
                        document[key] = sub
                    else:
                        document[key] = '{}#{}'.format(referrant_file, sub)
                elif isinstance(value, list):
                    new_sources = list()
                    for entry in value:
                        if entry.startswith('#' + doc_id):
                            new_sources.append(entry[len(doc_id)+2:])
                        else:
                            new_sources.append(entry)
                    document[key] = new_sources
            elif key == '$import':
                rewrite_import(document)
            elif key == 'class' and value == 'SchemaDefRequirement':
                return rewrite_schemadef(document)
            else:
                imports.update(rewrite(value, doc_id))
    return imports

def rewrite_import(document):
    external_file = document['$import'].split("/")[0][1:]
    document['$import'] = external_file

def rewrite_types(field, entry_file, sameself):
    if isinstance(field, list) and not isinstance(field, Text):
        for entry in field:
            rewrite_types(entry, entry_file, sameself)
        return
    if isinstance(field, dict):
        for key, value in field.items():
            for name in ('type', 'items'):
                if key == name:
                    if isinstance(value, Text) and value.startswith(entry_file):
                        if sameself:
                            field[key] = value[len(entry_file)+1:]
                        else:
                            field[key] = "{d[0]}#{d[1]}".format(d=value[1:].split('/',1))
            if isinstance(value, dict):
                rewrite_types(value, entry_file, sameself)
            if isinstance(value, list) and not isinstance(value, Text):
                for entry in value:
                    rewrite_types(entry, entry_file, sameself)

def rewrite_schemadef(document):
    for entry in document['types']:
        if '$import' in entry:
            rewrite_import(entry)
        elif 'name' in entry and '/' in entry['name']:
            entry_file, entry['name'] = entry['name'].split('/')
            for field in entry['fields']:
                field['name'] = field['name'].split('/')[2]
                rewrite_types(field, entry_file, True)
            with open(entry_file[1:], "a") as entry_handle:
                yaml.dump([entry], entry_handle, Dumper=yaml.RoundTripDumper)
            entry['$import'] = entry_file[1:]
            del entry['name']
            del entry['type']
            del entry['fields']
    seen_imports = set()
    def seen_import(entry):
        if '$import' in entry:
            external_file = entry['$import']
            if external_file not in seen_imports:
                seen_imports.add(external_file)
                return True
            return False
        return True
    types = document['types']
    document['types'][:] = [entry for entry in types if seen_import(entry)]
    return seen_imports

if __name__ == "__main__":
    run(sys.argv[1:])


