import json
from pytest import fixture

DATA = {
    "restaurant": [
        {"id": 1, "name": "PastaBar", "cuisine": "Italian", "wifi": False},
        {"id": 2, "name": "Berlin Burrito Company", "cuisine": "Mexican", "wifi": True},
        {"id": 3, "name": "I due forni", "cuisine": "Italian", "wifi": False},
    ]
}


@fixture
def data_file(tmpdir):
    data_file = str(tmpdir.mkdir("knowledge-base").join("data.json"))
    with open(data_file, "w", encoding="utf-8") as outfile:
        json.dump(DATA, outfile)
    return data_file
