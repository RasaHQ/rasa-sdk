## happy path
* request_restaurant
    - restaurant_form
    - form{"name": "restaurant_form"}
    - form{"name": null}
* thank
    - utter_noworries

## unhappy path
* request_restaurant
    - restaurant_form
    - form{"name": "restaurant_form"}
* chitchat
    - utter_chitchat
    - restaurant_form
* chitchat
    - utter_chitchat
    - restaurant_form
* chitchat
    - utter_chitchat
    - restaurant_form
    - form{"name": null}
* thank
    - utter_noworries

## unhappy path
* request_restaurant
    - restaurant_form
    - form{"name": "restaurant_form"}
* thank
    - utter_chitchat
    - restaurant_form
    - form{"name": null}
* thank
    - utter_noworries