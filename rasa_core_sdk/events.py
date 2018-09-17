from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from typing import Dict, Text, Any

logger = logging.getLogger(__name__)

EventType = Dict[Text, Any]


# noinspection PyPep8Naming
def UserUttered(text,
                parse_data=None,
                timestamp=None):
    return {
        "event": "user",
        "timestamp": timestamp,
        "text": text,
        "parse_data": parse_data,
    }


# noinspection PyPep8Naming
def BotUttered(text=None, data=None, timestamp=None):
    return {
        "event": "bot",
        "timestamp": timestamp,
        "text": text,
        "data": data,
    }


# noinspection PyPep8Naming
def SlotSet(key, value=None, timestamp=None):
    return {
        "event": "slot",
        "timestamp": timestamp,
        "name": key,
        "value": value,
    }


# noinspection PyPep8Naming
def Restarted(timestamp=None):
    return {
        "event": "restart",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def UserUtteranceReverted(timestamp=None):
    return {
        "event": "rewind",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def AllSlotsReset(timestamp=None):
    return {
        "event": "reset_slots",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def ReminderScheduled(action_name, trigger_date_time, name=None,
                      kill_on_user_message=True, timestamp=None):
    return {
        "event": "reminder",
        "timestamp": timestamp,
        "action": action_name,
        "date_time": trigger_date_time.isoformat(),
        "name": name,
        "kill_on_user_msg": kill_on_user_message
    }


# noinspection PyPep8Naming
def ActionReverted(timestamp=None):
    return {
        "event": "undo",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def StoryExported(timestamp=None):
    return {
        "event": "export",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def FollowupAction(name,
                   timestamp=None):
    return {
        "event": "followup",
        "timestamp": timestamp,
        "name": name,
    }


# noinspection PyPep8Naming
def ConversationPaused(timestamp=None):
    return {
        "event": "pause",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def ConversationResumed(timestamp=None):
    return {
        "event": "resume",
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def ActionExecuted(action_name, timestamp=None):
    return {
        "event": "action",
        "name": action_name,
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def AgentUttered(text=None, data=None, timestamp=None):
    return {
        "event": "agent",
        "text": text,
        "data": data,
        "timestamp": timestamp,
    }


# noinspection PyPep8Naming
def StartForm(form_name, timestamp=None):
    return {
        "event": 'start_form',
        "form_name": form_name,
        "timestamp": timestamp
    }


# noinspection PyPep8Naming
def EndForm(timestamp=None):
    return {
        "event": "end_form",
        "timestamp": timestamp
    }


# noinspection PyPep8Naming
def FormListen(timestamp=None):
    return {
        "event": "form_listen",
        "timestamp": timestamp
    }
