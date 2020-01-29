import pytest

from rasa_sdk.knowledge_base.storage import InMemoryKnowledgeBase


@pytest.mark.parametrize(
    "object_type,attributes,expected_length",
    [
        ("restaurant", [], 3),
        ("hotel", [], 0),
        ("restaurant", [{"name": "wifi", "value": True}], 1),
        ("restaurant", [{"name": "cuisine", "value": "Italian"}], 2),
    ],
)
async def test_query_entities(data_file, object_type, attributes, expected_length):
    knowledge_base = InMemoryKnowledgeBase(data_file)

    entities = await knowledge_base.get_objects(
        object_type=object_type, attributes=attributes
    )
    assert expected_length == len(entities)


@pytest.mark.parametrize(
    "object_type,object_identifier,expected_value",
    [
        (
            "restaurant",
            "1",
            {"id": 1, "name": "PastaBar", "cuisine": "Italian", "wifi": False},
        ),
        (
            "restaurant",
            "Burrito Company",
            {
                "id": 2,
                "name": "Berlin Burrito Company",
                "cuisine": "Mexican",
                "wifi": True,
            },
        ),
        ("restaurant", "non-existing", None),
        ("hotel", None, None),
    ],
)
async def test_query_object(data_file, object_type, object_identifier, expected_value):
    knowledge_base = InMemoryKnowledgeBase(data_file)

    actual_value = await knowledge_base.get_object(
        object_type=object_type, object_identifier=object_identifier
    )

    assert expected_value == actual_value


@pytest.mark.parametrize(
    "object_type,expected_attributes",
    [("restaurant", ["id", "name", "cuisine", "wifi"])],
)
async def test_get_attributes_for(data_file, object_type, expected_attributes):
    knowledge_base = InMemoryKnowledgeBase(data_file)

    actual_attributes = await knowledge_base.get_attributes_of_object(
        object_type=object_type
    )

    assert set(expected_attributes) == set(actual_attributes)


@pytest.mark.parametrize(
    "object_type,set_key_attribute,expected_key_attribute",
    [("restaurant", None, "id"), ("restaurant", "name", "name")],
)
async def test_key_attribute_of_object(
    data_file, object_type, set_key_attribute, expected_key_attribute
):
    knowledge_base = InMemoryKnowledgeBase(data_file)
    if set_key_attribute:
        knowledge_base.set_key_attribute_of_object(object_type, set_key_attribute)

    actual_key_attribute = await knowledge_base.get_key_attribute_of_object(
        object_type=object_type
    )

    assert expected_key_attribute == actual_key_attribute


@pytest.mark.parametrize(
    "object_type,set_repr_function,expected_repr_function",
    [
        ("restaurant", None, lambda obj: obj["name"]),
        (
            "restaurant",
            lambda obj: "restaurant: " + obj["name"],
            lambda obj: "restaurant: " + obj["name"],
        ),
    ],
)
async def test_get_representation_function_of_object(
    data_file, object_type, set_repr_function, expected_repr_function
):
    knowledge_base = InMemoryKnowledgeBase(data_file)
    if set_repr_function:
        knowledge_base.set_representation_function_of_object(
            object_type, set_repr_function
        )

    actual_repr_function = await knowledge_base.get_representation_function_of_object(
        object_type=object_type
    )

    dummy_object = await knowledge_base.get_object(object_type, 1)

    assert expected_repr_function(dummy_object) == actual_repr_function(dummy_object)
