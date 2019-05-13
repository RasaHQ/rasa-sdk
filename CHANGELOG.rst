Change Log
==========

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning`_ starting with version 0.11.0.

.. _master-release:

[Unreleased 1.0.0rc4] - `master`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: This version is not yet released and is under active development.

Added
-----

Changed
-------

Fixed
-----

Removed
-------

[1.0.0rc3] - 2019-05-13
^^^^^^^^^^^^^^^^^^^^^^^

Changed
-------
- package renamed from ``rasa_core_sdk`` to ``rasa_sdk`` - please make sure to
  update your imports accordingly

[1.0.0rc1] - 2019-05-09
^^^^^^^^^^^^^^^^^^^^^^^

Compatibility release for Rasa Core 1.0.0. There have not been any
additional changes when compared to ``0.14.0``.


[0.14.0] - 2019-04-26
^^^^^^^^^^^^^^^^^^^^^

Compatibility release for Rasa Core 0.14.0. There have not been any
additional changes when compared to ``0.13.1``.

[0.13.1] - 2019-04-16
^^^^^^^^^^^^^^^^^^^^^

Added
-----
- add formatter 'black'
- Slots filled before the start of a form are now validated upon form start
- In debug mode, the values of required slots for a form are now printed
  before submitting

Changed
-------
- validate_{} functions for slots now return dictionaries of form {slot: value}
  instead of value

Fixed
-----
- Slots extracted from entities in user input upon calling form activation are
  now correctly validated

[0.13.0] - 2019-03-26
^^^^^^^^^^^^^^^^^^^^^

Added
-----
- Abstract Actions can now be subclassed
- add warning in case of mismatched version of rasa_core and rasa_core_sdk
- ``FormAction.from_trigger_intent`` allows slot extraction from message
  triggering the FormAction
- ``Tracker.active_form`` now includes ``trigger_message`` attribute to allow
  access to message triggering the form

[0.12.2] - 2019-02-17
^^^^^^^^^^^^^^^^^^^^^

Added
-----
- add optional `validate_{slot}` methods to `FormAction`
- forms can now be deactivated during the validation function by returning
  `self.deactivate()`
- Function to get latest input channel from the tracker with
  ``tracker.get_latest_input_channel()``

Changed
-------
- ``self._deactivate()`` method from the ``FormAction`` class has been
  renamed to ``self.deactivate()``
- changed endpoint function so that it is now accessible with Python as well

[0.12.1] - 2018-11-11
^^^^^^^^^^^^^^^^^^^^^

Fixed
-----
- doc formatting preventing successful rasa core travis build

[0.12.0] - 2018-11-11
^^^^^^^^^^^^^^^^^^^^^

Added
-----
- added Dockerfile for rasa_core_sdk
- add ``active_form`` and ``latest_action_name`` properties to ``Tracker``
- add ``FormAction.slot_mapping()`` method to specify the mapping between
  user input and requested slot in the form
- add helper methods ``FormAction.from_entity(...)``,
  ``FormAction.from_intent(...)`` and ``FormAction.from_text(...)``
- add ``FormAction.validate(...)`` method to validate user input
- add warning in case of mismatched version of rasa_core and rasa_core_sdk

Changed
-------

- ``FormAction`` class was completely refactored
- ``required_fields()`` is changed to ``required_slots(tracker)``
- moved ``FormAction.get_other_slots(...)`` functionality to
  ``FormAction.extract_other_slots(...)``
- moved ``FormAction.get_requested_slot(...)`` functionality to
  ``FormAction.extract_requested_slot(...)``
- logic of requesting next slot can be customized in
  ``FormAction.request_next_slot(...)`` method

Removed
-------

- ``FormField`` class and its subclasses

Fixed
-----

[0.11.5] - 2018-09-24
^^^^^^^^^^^^^^^^^^^^^

Fixed
-----
- current state call in tracker

[0.11.4] - 2018-09-17
^^^^^^^^^^^^^^^^^^^^^

Fixed
-----
- wrong event name for the ``AgentUttered`` event - due to the wrong name,
  rasa core would deserialise the wrong event.


.. _`master`: https://github.com/RasaHQ/rasa_core/

.. _`Semantic Versioning`: http://semver.org/
