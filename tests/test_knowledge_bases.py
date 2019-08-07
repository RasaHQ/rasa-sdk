import pytest

from rasa_sdk.knowledge_bases import InMemoryKnowledgeBase

SCHEMA = {
    "restaurant": {
        "attributes": ["name", "cuisine", "wifi"],
        "key": "name",
        "representation": ["name"],
    }
}

GRAPH = {
    "restaurant": [
        {
            "name": "PastaBar",
            "cuisine": "Italian",
            "wifi": False,
        },
        {
            "name": "Berlin Burrito Company",
            "cuisine": "Mexican",
            "wifi": True,
        },
        {
            "name": "I due forni",
            "cuisine": "Italian",
            "wifi": False,
        }
    ]
}


def test_schema_validation():
    schema = {
        "correct_entity_type": {
            "attributes": ["a1", "a2"],
            "key": "key",
            "representation": ["a1", "a2"],
        },
        "incorrect_entity_1": {
            "attributes": ["a1", "a2"],
            "representation": ["a1", "a2"],
        },
        "incorrect_entity_2": {"key": "a1"},
    }

    graph = {"correct_entity_type": [{"a1": "value1", "a2": "value2"}]}

    with pytest.raises(ValueError) as excinfo:
        InMemoryKnowledgeBase(schema, graph)

    assert "incorrect_entity_1" in str(excinfo.value)


@pytest.mark.parametrize(
    "entity_type,attributes,expected_length", [
        ("restaurant", [], 3),
        ("hotel", [], 0),
        ("restaurant", [{"key": "wifi", "value": True}], 1),
        ("restaurant", [{"key": "cuisine", "value": "Italian"}], 2)
    ]
)
def test_query_entities(entity_type, attributes, expected_length):
    knowledge_base = InMemoryKnowledgeBase(SCHEMA, GRAPH)

    entities = knowledge_base.get_entities(entity_type=entity_type, attributes=attributes)
    assert expected_length == len(entities)


@pytest.mark.parametrize(
    "entity_type,key_attribute_value,attribute,expected_value", [
        ("restaurant", "PastaBar", "wifi", False),
        ("restaurant", "non-existing", "wifi", None),
        ("restaurant", "Berlin Burrito Company", "non-existing", None),
        ("hotel", "any-hotel", "any-attribute", None),
        ("restaurant", "Berlin Burrito Company", "cuisine", "Mexican"),
    ]
)
def test_query_attribute(entity_type, key_attribute_value, attribute, expected_value):
    knowledge_base = InMemoryKnowledgeBase(SCHEMA, GRAPH)

    actual_value = knowledge_base.get_attribute_of(entity_type=entity_type,
                                    key_attribute_value=key_attribute_value,
                                    attribute=attribute)

    assert expected_value == actual_value