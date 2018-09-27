## Generated Story -9155310465400161964
* request_restaurant
    - restaurant_form
    - form{"name": "restaurant_form"}
    - slot{"requested_slot": "cuisine"}
* chitchat
    - utter_chitchat
    - restaurant_form
    - form: slot{"requested_slot": "cuisine"}
* form: inform{"cuisine": "1"}
    - form: slot{"cuisine": "1"}
    - form: restaurant_form
    - form: slot{"cuisine": "1"}
    - form: slot{"requested_slot": "num_people"}
* form: inform{"num_people": "1"}
    - form: slot{"num_people": "1"}
    - form: restaurant_form
    - form: slot{"num_people": "1"}
    - form{"name": null}
    - slot{"requested_slot": null}
* thank
    - utter_noworries


## Generated Story 2392181920552359166
* request_restaurant
    - restaurant_form
    - form{"name": "restaurant_form"}
    - form: slot{"requested_slot": "cuisine"}
* form: inform{"cuisine": "1"}
    - form: slot{"cuisine": "1"}
    - form: restaurant_form
    - slot{"cuisine": "1"}
    - slot{"requested_slot": "num_people"}
* chitchat
    - utter_chitchat
    - restaurant_form
    - slot{"requested_slot": "num_people"}
* chitchat
    - utter_chitchat
    - restaurant_form
    - slot{"requested_slot": "num_people"}
* chitchat
    - utter_chitchat
    - restaurant_form
    - form: slot{"requested_slot": "num_people"}
* form: inform{"num_people": "1"}
    - form: slot{"num_people": "1"}
    - form: restaurant_form
    - form: slot{"num_people": "1"}
    - form{"name": null}
    - slot{"requested_slot": null}
* thank
    - utter_noworries
