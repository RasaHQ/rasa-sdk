import logging
from typing import List, Dict, Any, Optional, Text


logger = logging.getLogger(__name__)


class KnowledgeBase(object):

    def __init__(self, schema: Dict):
        self.schema = schema

    def get_entities(
        self,
        entity_type: Text,
        attributes: Optional[List[Dict[Text, Text]]] = None,
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
        self, entity_type: Text, key_attribute: Text, key_attribute_value: Text, attribute: Text
    ) -> Any:
        """
        Get the value of the given attribute for the provided entity.

        :param entity_type: entity type
        :param key_attribute: key attribute of entity
        :param key_attribute_value: value of the key attribute
        :param attribute: attribute of interest

        :return: the value of the attribute of interest
        """
        raise NotImplementedError("Method is not implemented.")


class InMemoryKnowledgeBase(KnowledgeBase):

    def __init__(self, schema: Dict, graph: Dict):
        self.graph = graph
        super().__init__(schema)

    def get_entities(
        self,
        entity_type: Text,
        attributes: Optional[List[Dict[Text, Text]]] = None,
        limit: int = 5,
    ) -> List[Dict[Text, Any]]:

        if entity_type not in self.graph:
            return []

        entities = self.graph[entity_type]

        # filter entities by attributes
        if attributes:
            entities = list(
                filter(
                    lambda e: [e[a["key"]] == a["value"] for a in attributes].count(
                        False
                    )
                    == 0,
                    entities,
                )
            )

        return entities[:limit]

    def get_attribute_of(
        self, entity_type: Text, key_attribute: Text, entity: Text, attribute: Text
    ) -> Any:
        if entity_type not in self.graph:
            return None

        entities = self.graph[entity_type]

        entity_of_interest = list(
            filter(lambda e: e[key_attribute] == entity, entities)
        )

        if not entity_of_interest or len(entity_of_interest) > 1:
            return None

        return entity_of_interest[0][attribute]

