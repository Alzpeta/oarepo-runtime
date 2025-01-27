import operator
from copy import deepcopy
from functools import reduce

from deepmerge import always_merger
from invenio_records.dumpers import SearchDumperExt


def getFromDict(dataDict, mapList):

    return reduce(operator.getitem, mapList, dataDict)

class MultilingualDumper(SearchDumperExt):
    paths = []
    SUPPORTED_LANGS = []

    def dump(self, record, data):

        for path in self.__class__.paths:
            new_elements = {}
            record2 = record
            path_array = path.split("/")
            path_array2 = []

            for x in path_array:
                path_array2.append(x)

            path_array2.pop(0)
            path_array2 = path_array2[:-1]

            for x in path_array2:
                if x in record2:
                    record2 = record2[x]
            path_array.pop(0)
            try:
                multilingual_element = getFromDict(record, path_array)
            except:
                multilingual_element = []
            for rec in multilingual_element:
                if rec["lang"] in self.__class__.SUPPORTED_LANGS:
                    el_name = path_array[-1] + "_" + rec["lang"]
                    always_merger.merge(new_elements, {el_name: rec["value"]})

            always_merger.merge(record2, new_elements)
        data.update(deepcopy(dict(record)))
        return data

    def load(self, record, data):

        for path in self.__class__.paths:
            record2 = record
            path_array = path.split("/")
            path_array2 = []
            for x in path_array:
                path_array2.append(x)

            path_array2.pop(0)
            path_array2 = path_array2[:-1]

            ok = True
            for x in path_array2:
                if x not in record2:
                    ok = False
                    break
                record2 = record2[x]
            if not ok:
                continue

            path_array.pop(0)
            try:
                multilingual_element = getFromDict(record, path_array)
            except: multilingual_element = []
            for rec in multilingual_element:
                if rec["lang"] in self.__class__.SUPPORTED_LANGS:
                    el_name = path_array[-1] + "_" + rec["lang"]
                    del record2[el_name]
        return data
