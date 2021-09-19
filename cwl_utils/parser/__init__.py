# SPDX-License-Identifier: Apache-2.0

from schema_salad.exceptions import ValidationException
from schema_salad.utils import yaml_no_ts
import cwl_utils.parser.parser_v1_0 as cwl_v1_0
import cwl_utils.parser.parser_v1_1 as cwl_v1_1
import cwl_utils.parser.parser_v1_2 as cwl_v1_2

import os
from typing import MutableMapping, MutableSequence, Union, Optional

LoadingOptions = Union[cwl_v1_0.LoadingOptions, cwl_v1_1.LoadingOptions, cwl_v1_2.LoadingOptions]
Savable = Union[cwl_v1_0.Savable, cwl_v1_1.Savable, cwl_v1_2.Savable]
save_type = Union[cwl_v1_0.save_type, cwl_v1_1.save_type, cwl_v1_2.save_type]


def cwl_version(yaml: MutableMapping) -> Optional[str]:
    if 'cwlVersion' not in list(yaml.keys()):
        return None
    return yaml['cwlVersion']
        

def load_document(doc: Union[str, MutableMapping], baseuri: Optional[str] = None,
                  loadingOptions: Optional[LoadingOptions] = None) -> Union[Savable, MutableSequence[Savable]]:
    if baseuri is None:
        baseuri = cwl_v1_0.file_uri(os.getcwd()) + "/"
    if isinstance(doc, str):
        return load_document_by_string(doc, baseuri, loadingOptions)
    return load_document_by_yaml(doc, baseuri, loadingOptions)


def load_document_by_string(string: str, uri: str, loadingOptions: Optional[LoadingOptions] = None) -> Union[Savable, MutableSequence[Savable]]:
    yaml = yaml_no_ts()
    result = yaml.load(string)
    return load_document_by_yaml(result, uri, loadingOptions)


def load_document_by_yaml(yaml: MutableMapping, uri: str, loadingOptions: Optional[LoadingOptions] = None) -> Union[Savable, MutableSequence[Savable]]:
    version = cwl_version(yaml)
    if version == 'v1.0':
        result = cwl_v1_0.load_document_by_yaml(yaml, uri, loadingOptions)
    elif version == 'v1.1':
        result = cwl_v1_1.load_document_by_yaml(yaml, uri, loadingOptions)
    elif version == 'v1.2':
        result = cwl_v1_2.load_document_by_yaml(yaml, uri, loadingOptions)
    elif version is None:
        raise ValidationException("could not get the cwlVersion")
    else:
        raise ValidationException("Version error. Did not recognise {} as a CWL version".format(version))

    if isinstance(result, MutableSequence):
        lst = []
        for r in result:
            if 'cwlVersion' in r.attrs:
                r.cwlVersion = version
            lst.append(r)
        return lst
    return result


def save(val: Optional[Union[Savable, MutableSequence[Savable]]],
         top: bool = True,
         base_url: str = "",
         relative_uris: bool = True) -> save_type:
    if (
        isinstance(val, cwl_v1_0.Savable)
        or isinstance(val, cwl_v1_1.Savable)
        or isinstance(val, cwl_v1_2.Savable)
    ):
        return val.save(top=top, base_url=base_url, relative_uris=relative_uris)
    if isinstance(val, MutableSequence):
        lst = [
            save(v, top=top, base_url=base_url, relative_uris=relative_uris)
            for v in val
        ]
        if top and all((isinstance(v, cwl_v1_0.Process)
                        or isinstance(v, cwl_v1_1.Process)
                        or isinstance(v, cwl_v1_2.Process) for v in val)):
            return {
                'cwlVersion': lst[0]['cwlVersion'],
                '$graph': lst
            }
        return lst
    if isinstance(val, MutableMapping):
        newdict = {}
        for key in val:
            newdict[key] = save(
                val[key], top=False, base_url=base_url, relative_uris=relative_uris
            )
        return newdict
    return val
