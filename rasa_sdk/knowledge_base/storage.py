import logging
import random


logger = logging.getLogger(__name__)


SCHEMA_KEYS_KEY = "key"
SCHEMA_KEYS_ATTRIBUTES = "attributes"
SCHEMA_KEYS_REPRESENTATION = "representation"
MANDATORY_SCHEMA_KEYS = [
    SCHEMA_KEYS_KEY,
    SCHEMA_KEYS_ATTRIBUTES,
    SCHEMA_KEYS_REPRESENTATION,
]


class KnowledgeBase(object):
    def __init__(self, schema):
        self.ordinal_mention_mapping = {
            "1": lambda l: l[0],
            "2": lambda l: l[1],
            "3": lambda l: l[2],
            "4": lambda l: l[3],
            "5": lambda l: l[4],
            "6": lambda l: l[5],
            "7": lambda l: l[6],
            "8": lambda l: l[7],
            "9": lambda l: l[8],
            "10": lambda l: l[9],
            "ANY": lambda l: random.choice(list),
            "LAST": lambda l: l[-1],
        }

        self.schema = schema
        self._validate_schema()

    def _validate_schema(self):
        for object_type, values in self.schema.items():
            if not set(values.keys()) == set(MANDATORY_SCHEMA_KEYS):
                raise ValueError(
                    "The provided schema is missing mandatory keys for"
                    "object type '{}'. The mandatory keys are: {}".format(
                        object_type, MANDATORY_SCHEMA_KEYS
                    )
                )

    def set_ordinal_mention_mapping(self, mapping):
        """
        Overwrites the default ordinal mention mapping. E.g. the mapping that
        maps, for example, "first one" to the first element in a list.

        Args:
            mapping: the ordinal mention mapping
        """
        self.ordinal_mention_mapping = mapping

    def get_objects(self, object_type, attributes, limit=5):
        """
        Query the knowledge base for objects of the given type. Restrict the objects
        by the provided attributes, if any attributes are given.

        Args:
            object_type: the object type
            attributes: list of attributes
            limit: maximum number of objects to return

        Returns: list of objects
        """
        raise NotImplementedError("Method is not implemented.")

    def get_attribute_of(self, object_type, key_attribute_value, attribute):
        """
        Get the value of the given attribute for the provided object.

        Args:
            object_type: object type
            key_attribute_value: value of the key attribute
            attribute: attribute of interest

        Returns: the value of the attribute of interest
        """
        raise NotImplementedError("Method is not implemented.")


class InMemoryKnowledgeBase(KnowledgeBase):
    def __init__(self, schema, data):
        self.data = data
        super(InMemoryKnowledgeBase, self).__init__(schema)

    def get_objects(self, object_type, attributes, limit=5):

        if object_type not in self.data:
            return []

        objects = self.data[object_type]

        # filter objects by attributes
        if attributes:
            objects = list(
                filter(
                    lambda obj: [
                        obj[a["name"]] == a["value"] for a in attributes
                    ].count(False)
                    == 0,
                    objects,
                )
            )

        random.shuffle(objects)

        return objects[:limit]

    def get_attribute_of(self, object_type, key_attribute_value, attribute):
        if object_type not in self.data:
            return None

        objects = self.data[object_type]
        key_attribute = self.schema[object_type][SCHEMA_KEYS_KEY]

        object_of_interest = list(
            filter(lambda obj: obj[key_attribute] == key_attribute_value, objects)
        )

        if not object_of_interest or len(object_of_interest) > 1:
            return None

        object_of_interest = object_of_interest[0]

        if attribute not in object_of_interest:
            return None

        return object_of_interest[attribute]
