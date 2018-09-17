## happy path               <!-- name of the story - just for debugging -->
* greet
    - utter_greet
* request_restaurant
    - start_restaurant
    - slot{"form_complete": true}
    - utter_book_restaurant

## unhappy path
* greet
    - utter_greet
* request_restaurant
    - start_restaurant
    - slot{"form_complete": false}
    - utter_happy
* request_restaurant
    - start_restaurant
    - slot{"form_complete": true}
    - utter_book_restaurant