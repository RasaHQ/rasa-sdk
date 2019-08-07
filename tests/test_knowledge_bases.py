import pytest

from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase, SCHEMA_KEYS_KEY, \
    SCHEMA_KEYS_ATTRIBUTES, SCHEMA_KEYS_REPRESENTATION, Attribute

SCHEMA = {
    "restaurant": {
        SCHEMA_KEYS_ATTRIBUTES: ["name", "cuisine", "wifi"],
        SCHEMA_KEYS_KEY: "name",
        SCHEMA_KEYS_REPRESENTATION: lambda e: e["name"],
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
            SCHEMA_KEYS_ATTRIBUTES: ["a1", "a2"],
            SCHEMA_KEYS_KEY: "key",
            SCHEMA_KEYS_REPRESENTATION: lambda e: e["a2"],
        },
        "incorrect_entity_1": {
            SCHEMA_KEYS_ATTRIBUTES: ["a1", "a2"],
            SCHEMA_KEYS_REPRESENTATION: lambda e: e["a1"],
        },
        "incorrect_entity_2": {SCHEMA_KEYS_KEY: "a1"},
    }

    graph = {"correct_entity_type": [{"a1": "value1", "a2": "value2"}]}

    with pytest.raises(ValueError) as excinfo:
        InMemoryKnowledgeBase(schema, graph)

    assert "incorrect_entity_1" in str(excinfo.value)


@pytest.mark.parametrize(
    "entity_type,attributes,expected_length", [
        ("restaurant", [], 3),
        ("hotel", [], 0),
        ("restaurant", [Attribute("wifi", True)], 1),
        ("restaurant", [Attribute("cuisine", "Italian")], 2)
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