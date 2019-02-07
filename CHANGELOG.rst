Change Log
==========

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning`_ starting with version 0.11.0.

.. _master-release:

[Unreleased 0.12.0.aX] - `master`_
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: This version is not yet released and is under active development.

Added
-----
- add optional `validate_{slot}` methods to `FormAction`
- forms can now be deactivated during the validation function by returning
  `self.deactivate()`

Removed
-------

Changed
-------
- `self._deactivate()` renamed to `self.deactivate()`

Fixed
-----

[0.12.1] - 2018-11-11
^^^^^^^^^^^^^^^^^^^^^

Fixed
-----
- doc formatting preventing successfull rasa core travis build

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
