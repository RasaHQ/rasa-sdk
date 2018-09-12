
from rasa_core_sdk.slots import Slot

class MyFreeTextSlot(Slot):

    def name(self):
        return "my_free_text_slot"

    def validate(self, parse_data):
        new_parse_data = parse_data.copy()
        del new_parse_data["entities"]
        text = parse_data.get("text")
        new_parse_data["slots"] = {}
        new_parse_data["slots"][self.name()] = text
        return new_parse_data
