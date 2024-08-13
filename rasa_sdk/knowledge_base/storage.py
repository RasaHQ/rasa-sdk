import json
import logging
import os
import random
from typing import DefaultDict, Text, Callable, Dict, List, Any, Optional
from collections import defaultdict

from rasa_sdk import utils

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self) -> None:
        """Create a new knowledge base."""
        self.ordinal_mention_mapping = {
            "1": lambda lst: lst[0],
            "2": lambda lst: lst[1],
            "3": lambda lst: lst[2],
            "4": lambda lst: lst[3],
            "5": lambda lst: lst[4],
            "6": lambda lst: lst[5],
            "7": lambda lst: lst[6],
            "8": lambda lst: lst[7],
            "9": lambda lst: lst[8],
            "10": lambda lst: lst[9],
            "ANY": lambda lst: random.choice(lst),
            "LAST": lambda lst: lst[-1],
        }

        self.key_attribute: DefaultDict[Text, Text] = defaultdict(lambda: "id")
        self.representation_function: DefaultDict[
            Text, Callable[[Dict[Text, Text]], Text]
        ] = defaultdict(lambda: lambda obj: obj["name"])

    async def get_attributes_of_object(self, object_type: Text) -> List[Text]:
        """Returns a list of all attributes that belong to the provided object type.

        Args:
            object_type: the object type

        Returns: list of attributes of object_type
        """
        raise NotImplementedError("Method is not implemented.")

    async def get_key_attribute_of_object(self, object_type: Text) -> Text:
        """Returns the key attribute for the given object type.

        Args:
            object_type: the object type

        Returns: key attribute
        """
        return self.key_attribute[object_type]

    async def get_representation_function_of_object(
        self, object_type: Text
    ) -> Callable:
        """Returns a lambda function that returns string representation of the object.

        Args:
            object_type: the object type

        Returns: lambda function
        """
        return self.representation_function[object_type]

    def set_ordinal_mention_mapping(self, mapping: Dict[Text, Callable]) -> None:
        """Overwrites the default ordinal mention mapping.

        E.g. the mapping that maps, for example,
        "first one" to the first element in a list.

        Args:
            mapping: the ordinal mention mapping
        """
        self.ordinal_mention_mapping = mapping

    async def get_objects(
        self, object_type: Text, attributes: List[Dict[Text, Text]], limit: int = 5
    ) -> List[Dict[Text, Any]]:
        """Query the knowledge base for objects of the given type.

        Restrict the objects by the provided attributes,
        if any attributes are given.

        Args:
            object_type: the object type
            attributes: list of attributes
            limit: maximum number of objects to return

        Returns: list of objects
        """
        raise NotImplementedError("Method is not implemented.")

    async def get_object(
        self, object_type: Text, object_identifier: Text
    ) -> Optional[Dict[Text, Any]]:
        """Returns the object of the given type and identifier.

        Args:
            object_type: the object type
            object_identifier: value of the key attribute or the string
            representation of the object

        Returns: the object of interest
        """
        raise NotImplementedError("Method is not implemented.")

    def get_object_types(self) -> List[Text]:
        """Returns a list of object types from knowledge base data."""
        raise NotImplementedError("Method is not implemented.")


class InMemoryKnowledgeBase(KnowledgeBase):
    def __init__(self, data_file: Text) -> None:
        """Initialize the in-memory knowledge base.

        Loads the data from the given data file into memory.

        Args:
            data_file: the path to the file containing the data
        """
        self.data_file = data_file
        self.data: Dict[Text, Any] = {}
        self.load()
        super().__init__()

    def load(self) -> None:
        """Load the data from the file in an in-memory knowledge base."""
        try:
            with open(self.data_file, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            raise ValueError(f"File '{self.data_file}' does not exist.")

        try:
            self.data = json.loads(content)
        except ValueError as e:
            raise ValueError(
                f"Failed to read json from "
                f"'{os.path.abspath(self.data_file)}'. Error: {e}"
            )

    def set_representation_function_of_object(
        self, object_type: Text, representation_function: Callable
    ) -> None:
        """Set the representation function of the given object type.

        Args:
            object_type: the object type
            representation_function: the representation function
        """
        self.representation_function[object_type] = representation_function

    def set_key_attribute_of_object(
        self, object_type: Text, key_attribute: Text
    ) -> None:
        """Set the key attribute of the given object type.

        Args:
            object_type: the object type
            key_attribute: the name of the key attribute
        """
        self.key_attribute[object_type] = key_attribute

    async def get_attributes_of_object(self, object_type: Text) -> List[Text]:
        """Returns attributes of the object.

        Args:
            object_type: the object type

        Returns: list of attributes of an object
        """
        if object_type not in self.data or not self.data[object_type]:
            return []

        first_object = self.data[object_type][0]

        return list(first_object.keys())

    async def get_objects(
        self, object_type: Text, attributes: List[Dict[Text, Text]], limit: int = 5
    ) -> List[Dict[Text, Any]]:
        """Returns objects of the given type.

        If attributes are specified,
        the objects are filtered by these attributes.

        Args:
            object_type: the object type
            attributes: list of attributes to filter the objects by
            limit: maximum number of objects to return
        """
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

    async def get_object(
        self, object_type: Text, object_identifier: Text
    ) -> Optional[Dict[Text, Any]]:
        """Returns the object of the given type and identifier.

        Args:
            object_type: the object type
            object_identifier: value of the key attribute or the string
            representation of the object

        Returns: the object of interest if found, else None
        """
        if object_type not in self.data:
            return None

        objects = self.data[object_type]
        key_attribute = await utils.call_potential_coroutine(
            self.get_key_attribute_of_object(object_type)
        )

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
            repr_function = await utils.call_potential_coroutine(
                self.get_representation_function_of_object(object_type)
            )

            objects_of_interest = list(
                filter(
                    lambda obj: str(object_identifier).lower()
                    in str(repr_function(obj)).lower(),
                    objects,
                )
            )

        if not objects_of_interest or len(objects_of_interest) > 1:
            # TODO:
            #  if multiple objects are found, the objects could be shown
            #  to the user. the user then needs to clarify what object he meant.
            return None

        return objects_of_interest[0]

    def get_object_types(self) -> List[Text]:
        """Returns a list of object types from knowledge base data.

        Returns:
            list of object types
        """
        return list(self.data.keys())
