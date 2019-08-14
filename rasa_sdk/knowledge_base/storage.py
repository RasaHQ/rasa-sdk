import json
import logging
import os
import random
from collections import defaultdict

logger = logging.getLogger(__name__)


class KnowledgeBase(object):
    def __init__(self):

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

        self.key_attribute = defaultdict(lambda: "id")
        self.representation_function = defaultdict(lambda: lambda obj: obj["name"])

    def get_attributes_of_object(self, object_type):
        """
        Returns a list of all attributes that belong to the provided object type.

        Args:
            object_type: the object type

        Returns: list of attributes of object_type
        """
        raise NotImplementedError("Method is not implemented.")

    def get_key_attribute_of_object(self, object_type):
        """
        Returns the key attribute for the given object type.

        Args:
            object_type: the object type

        Returns: key attribute
        """
        return self.key_attribute[object_type]

    def get_representation_function_of_object(self, object_type):
        """
        Returns a lamdba function that takes the object and returns a string
        representation of it.

        Args:
            object_type: the object type

        Returns: lamdba function
        """
        return self.representation_function[object_type]

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

    def get_object(self, object_type, object_identifier):
        """
        Returns the object of the given type with the given key attribute value.

        Args:
            object_type: the object type
            object_identifier: value of the key attribute or the string representation of the object

        Returns: the object of interest
        """
        raise NotImplementedError("Method is not implemented.")


class InMemoryKnowledgeBase(KnowledgeBase):
    def __init__(self, data):
        self.data = data
        super(InMemoryKnowledgeBase, self).__init__()

    @classmethod
    def load(cls, filename, encoding="utf-8"):
        """
        Load the data from the given file and initialize an in-memory knowledge base.

        Args:
            filename: path to the file that contains the data for the knoweldge base
            encoding: file encoding

        Returns: an in-memory knowledge base
        """
        try:
            with open(filename, encoding=encoding) as f:
                content = f.read()
        except FileNotFoundError:
            raise ValueError("File '{}' does not exist.".format(filename))

        try:
            data = json.loads(content)
            return cls(data)
        except ValueError as e:
            raise ValueError(
                "Failed to read json from '{}'. Error: "
                "{}".format(os.path.abspath(filename), e)
            )

    def set_representation_function_of_object(
        self, object_type, representation_function
    ):
        """
        Set the representation function of the given object type.

        Args:
            object_type: the object type
            representation_function: the representation function
        """
        self.representation_function[object_type] = representation_function

    def set_key_attribute_of_object(self, object_type, key_attribute):
        """
        Set the key attribute of the given object type.

        Args:
            object_type: the object type
            key_attribute: the name of the key attribute
        """
        self.key_attribute[object_type] = key_attribute

    def get_attributes_of_object(self, object_type):
        if object_type not in self.data or len(self.data[object_type]) < 1:
            return []

        first_object = self.data[object_type][0]

        return list(first_object.keys())

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

    def get_object(self, object_type, object_identifier):
        if object_type not in self.data:
            return None

        objects = self.data[object_type]
        key_attribute = self.get_key_attribute_of_object(object_type)

        # filter the objects by its key attribute, for example, 'id'
        objects_of_interest = list(
            filter(
                lambda obj: str(obj[key_attribute]).lower()
                == str(object_identifier).lower(),
                objects,
            )
        )

        # if the object was referred to directly, we need to compare the representation
        # of each object with the given object identifier
        if not objects_of_interest:
            repr_function = self.get_representation_function_of_object(object_type)
            objects_of_interest = list(
                filter(
                    lambda obj: str(object_identifier).lower()
                    in str(repr_function(obj)).lower(),
                    objects,
                )
            )

        if not objects_of_interest or len(objects_of_interest) > 1:
            return None

        return objects_of_interest[0]
