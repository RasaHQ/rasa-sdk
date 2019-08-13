import pytest

from rasa_sdk.knowledge_base.storage import (
    InMemoryKnowledgeBase,
)

DATA = {
    "restaurant": [
        {"id": "1", "name": "PastaBar", "cuisine": "Italian", "wifi": "False"},
        {"id": "2", "name": "Berlin Burrito Company", "cuisine": "Mexican", "wifi": "True"},
        {"id": "3", "name": "I due forni", "cuisine": "Italian", "wifi": "False"},
    ]
}


@pytest.mark.parametrize(
    "entity_type,attributes,expected_length",
    [
        ("restaurant", [], 3),
        ("hotel", [], 0),
        ("restaurant", [{"name": "wifi", "value": "True"}], 1),
        ("restaurant", [{"name": "cuisine", "value": "Italian"}], 2),
    ],
)
def test_query_entities(entity_type, attributes, expected_length):
    knowledge_base = InMemoryKnowledgeBase(DATA)

    entities = knowledge_base.get_objects(
        object_type=entity_type, attributes=attributes
    )
    assert expected_length == len(entities)


@pytest.mark.parametrize(
    "entity_type,key_attribute_value,attribute,expected_value",
    [
        ("restaurant", "1", "wifi", "False"),
        ("restaurant", "non-existing", "wifi", None),
        ("restaurant", "2", "non-existing", None),
        ("hotel", "any-hotel", "any-attribute", None),
        ("restaurant", "2", "cuisine", "Mexican"),
    ],
)
def test_query_attribute(entity_type, key_attribute_value, attribute, expected_value):
    knowledge_base = InMemoryKnowledgeBase(DATA)

    actual_value = knowledge_base.get_attribute(
        object_type=entity_type,
        key_attribute_value=key_attribute_value,
        attribute=attribute,
    )

    assert expected_value == actual_value


@pytest.mark.parametrize(
    "entity_type,expected_attributes",
    [
        ("restaurant", ["id", "name", "cuisine", "wifi"])
    ],
)
def test_get_attributes_for(entity_type, expected_attributes):
    knowledge_base = InMemoryKnowledgeBase(DATA)

    actual_attributes = knowledge_base.get_attributes_of_object(
        object_type=entity_type
    )

    assert expected_attributes == actual_attributes
