import logging
import random
from typing import List, Dict, Any, Optional, Text, Callable, NamedTuple

logger = logging.getLogger(__name__)


SCHEMA_KEYS_KEY = "key"
SCHEMA_KEYS_ATTRIBUTES = "attributes"
SCHEMA_KEYS_REPRESENTATION = "representation"
MANDATORY_SCHEMA_KEYS = [
    SCHEMA_KEYS_KEY,
    SCHEMA_KEYS_ATTRIBUTES,
    SCHEMA_KEYS_REPRESENTATION,
]


class Attribute(NamedTuple):
    name: List[Dict[Text, Any]]
    value: int


class KnowledgeBase(object):
    def __init__(self, schema: Dict[Text, Dict[Text, Any]]):
        self.ordinal_mention_mapping = {
            "one": lambda l: l[0],
            "first": lambda l: l[0],
            "1": lambda l: l[0],
            "first one": lambda l: l[0],
            "two": lambda l: l[1],
            "second": lambda l: l[1],
            "2": lambda l: l[1],
            "second one": lambda l: l[1],
            "three": lambda l: l[2],
            "third": lambda l: l[2],
            "3": lambda l: l[2],
            "third one": lambda l: l[2],
            "four": lambda l: l[3],
            "fourth": lambda l: l[3],
            "4": lambda l: l[3],
            "any": lambda l: random.choice(list),
            "last": lambda l: l[-1],
            "last one": lambda l: l[-1],
            "final": lambda l: l[-1],
        }

        self.schema = schema
        self._validate_schema()

    def _validate_schema(self):
        for entity_type, values in self.schema.items():
            if not set(values.keys()) == set(MANDATORY_SCHEMA_KEYS):
                raise ValueError(
                    "The provided schema is missing mandatory keys for"
                    "entity type '{}'. The mandatory keys are: {}".format(
                        entity_type, MANDATORY_SCHEMA_KEYS
                    )
                )

    def set_ordinal_mention_mapping(self, mapping: Dict[Text, Callable[[List], Any]]):
        """
        Overwrites the default ordinal mention mapping. E.g. the mapping that
        maps, for example, "first one" to the first element of the previously
        mentioned entities.

        :param mapping: the ordinal mention mapping
        """
        self.ordinal_mention_mapping = mapping

    def get_entities(
        self,
        entity_type: Text,
        attributes: Optional[List[Attribute]] = None,
        limit: int = 5,
    ) -> List[Dict[Text, Any]]:
        """
        Query the knowledge base for entities of the given type. Restrict the entities
        by the provided attributes, if any attributes are given.

        :param entity_type: the entity type
        :param attributes: list of attributes
        :param limit: maximum number of entities to return

        :return: list of entities
        """
        raise NotImplementedError("Method is not implemented.")

    def get_attribute_of(
        self, entity_type: Text, key_attribute_value: Text, attribute: Text
    ) -> Any:
        """
        Get the value of the given attribute for the provided entity.

        :param entity_type: entity type
        :param key_attribute_value: value of the key attribute
        :param attribute: attribute of interest

        :return: the value of the attribute of interest
        """
        raise NotImplementedError("Method is not implemented.")


class InMemoryKnowledgeBase(KnowledgeBase):
    def __init__(self, schema: Dict, data: Dict):
        self.data = data
        super().__init__(schema)

    def get_entities(
        self,
        entity_type: Text,
        attributes: Optional[List[Attribute]] = None,
        limit: int = 5,
    ) -> List[Dict[Text, Any]]:

        if entity_type not in self.data:
            return []

        entities = self.data[entity_type]

        # filter entities by attributes
        if attributes:
            entities = list(
                filter(
                    lambda e: [e[a.name] == a.value for a in attributes].count(False)
                    == 0,
                    entities,
                )
            )

        return entities[:limit]

    def get_attribute_of(
        self, entity_type: Text, key_attribute_value: Text, attribute: Text
    ) -> Any:
        if entity_type not in self.data:
            return None

        entities = self.data[entity_type]
        key_attribute = self.schema[entity_type][SCHEMA_KEYS_KEY]

        entity_of_interest = list(
            filter(lambda e: e[key_attribute] == key_attribute_value, entities)
        )

        if not entity_of_interest or len(entity_of_interest) > 1:
            return None

        entity = entity_of_interest[0]

        if attribute not in entity:
            return None

        return entity_of_interest[0][attribute]
