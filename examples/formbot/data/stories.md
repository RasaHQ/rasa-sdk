## happy path
* request_restaurant
    - restaurant_form
    - form_activated{"form_name": "restaurant_form"}
    - form_deactivated
* thank
    - utter_noworries

## unhappy path
* request_restaurant
    - restaurant_form
    - form_activated{"form_name": "restaurant_form"}
* chitchat
    - utter_chitchat
    - restaurant_form
    - form_deactivated
* thank
    - utter_noworries

## unhappy path
* request_restaurant
    - restaurant_form
    - form_activated{"form_name": "restaurant_form"}
* thank
    - utter_noworries
    - restaurant_form
    - form_deactivated
* thank
    - utter_noworries