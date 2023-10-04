# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: action_webhook.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14\x61\x63tion_webhook.proto\x12\x15\x61\x63tion_server_webhook\x1a\x19google/protobuf/any.proto\"\xf3\x04\n\x07Tracker\x12\x17\n\x0f\x63onversation_id\x18\x01 \x01(\t\x12\x38\n\x05slots\x18\x02 \x03(\x0b\x32).action_server_webhook.Tracker.SlotsEntry\x12I\n\x0elatest_message\x18\x03 \x03(\x0b\x32\x31.action_server_webhook.Tracker.LatestMessageEntry\x12\x19\n\x11latest_event_time\x18\x04 \x01(\x01\x12\x17\n\x0f\x66ollowup_action\x18\x05 \x01(\t\x12\x0e\n\x06paused\x18\x06 \x01(\x08\x12\x0e\n\x06\x65vents\x18\x07 \x03(\t\x12\x1c\n\x14latest_input_channel\x18\x08 \x01(\t\x12\x43\n\x0b\x61\x63tive_loop\x18\t \x03(\x0b\x32..action_server_webhook.Tracker.ActiveLoopEntry\x12G\n\rlatest_action\x18\n \x03(\x0b\x32\x30.action_server_webhook.Tracker.LatestActionEntry\x1a,\n\nSlotsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\x34\n\x12LatestMessageEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\x31\n\x0f\x41\x63tiveLoopEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\x33\n\x11LatestActionEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xfc\x04\n\x06\x44omain\x12\x39\n\x06\x63onfig\x18\x01 \x03(\x0b\x32).action_server_webhook.Domain.ConfigEntry\x12H\n\x0esession_config\x18\x02 \x03(\x0b\x32\x30.action_server_webhook.Domain.SessionConfigEntry\x12\x0f\n\x07intents\x18\x03 \x03(\t\x12\x10\n\x08\x65ntities\x18\x04 \x03(\t\x12\x37\n\x05slots\x18\x05 \x03(\x0b\x32(.action_server_webhook.Domain.SlotsEntry\x12?\n\tresponses\x18\x06 \x03(\x0b\x32,.action_server_webhook.Domain.ResponsesEntry\x12\x0f\n\x07\x61\x63tions\x18\x07 \x03(\t\x12\x37\n\x05\x66orms\x18\x08 \x03(\x0b\x32(.action_server_webhook.Domain.FormsEntry\x12\x13\n\x0b\x65\x32\x65_actions\x18\t \x03(\t\x1a-\n\x0b\x43onfigEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\x34\n\x12SessionConfigEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a,\n\nSlotsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a\x30\n\x0eResponsesEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a,\n\nFormsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xa9\x01\n\x0eWebhookRequest\x12\x13\n\x0bnext_action\x18\x01 \x01(\t\x12\x11\n\tsender_id\x18\x02 \x01(\t\x12/\n\x07tracker\x18\x03 \x01(\x0b\x32\x1e.action_server_webhook.Tracker\x12-\n\x06\x64omain\x18\x04 \x01(\x0b\x32\x1d.action_server_webhook.Domain\x12\x0f\n\x07version\x18\x05 \x01(\t\"`\n\x0fWebhookResponse\x12$\n\x06\x65vents\x18\x01 \x03(\x0b\x32\x14.google.protobuf.Any\x12\'\n\tresponses\x18\x02 \x03(\x0b\x32\x14.google.protobuf.Any2o\n\x13\x41\x63tionServerWebhook\x12X\n\x07webhook\x12%.action_server_webhook.WebhookRequest\x1a&.action_server_webhook.WebhookResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'action_webhook_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _TRACKER_SLOTSENTRY._options = None
  _TRACKER_SLOTSENTRY._serialized_options = b'8\001'
  _TRACKER_LATESTMESSAGEENTRY._options = None
  _TRACKER_LATESTMESSAGEENTRY._serialized_options = b'8\001'
  _TRACKER_ACTIVELOOPENTRY._options = None
  _TRACKER_ACTIVELOOPENTRY._serialized_options = b'8\001'
  _TRACKER_LATESTACTIONENTRY._options = None
  _TRACKER_LATESTACTIONENTRY._serialized_options = b'8\001'
  _DOMAIN_CONFIGENTRY._options = None
  _DOMAIN_CONFIGENTRY._serialized_options = b'8\001'
  _DOMAIN_SESSIONCONFIGENTRY._options = None
  _DOMAIN_SESSIONCONFIGENTRY._serialized_options = b'8\001'
  _DOMAIN_SLOTSENTRY._options = None
  _DOMAIN_SLOTSENTRY._serialized_options = b'8\001'
  _DOMAIN_RESPONSESENTRY._options = None
  _DOMAIN_RESPONSESENTRY._serialized_options = b'8\001'
  _DOMAIN_FORMSENTRY._options = None
  _DOMAIN_FORMSENTRY._serialized_options = b'8\001'
  _globals['_TRACKER']._serialized_start=75
  _globals['_TRACKER']._serialized_end=702
  _globals['_TRACKER_SLOTSENTRY']._serialized_start=500
  _globals['_TRACKER_SLOTSENTRY']._serialized_end=544
  _globals['_TRACKER_LATESTMESSAGEENTRY']._serialized_start=546
  _globals['_TRACKER_LATESTMESSAGEENTRY']._serialized_end=598
  _globals['_TRACKER_ACTIVELOOPENTRY']._serialized_start=600
  _globals['_TRACKER_ACTIVELOOPENTRY']._serialized_end=649
  _globals['_TRACKER_LATESTACTIONENTRY']._serialized_start=651
  _globals['_TRACKER_LATESTACTIONENTRY']._serialized_end=702
  _globals['_DOMAIN']._serialized_start=705
  _globals['_DOMAIN']._serialized_end=1341
  _globals['_DOMAIN_CONFIGENTRY']._serialized_start=1100
  _globals['_DOMAIN_CONFIGENTRY']._serialized_end=1145
  _globals['_DOMAIN_SESSIONCONFIGENTRY']._serialized_start=1147
  _globals['_DOMAIN_SESSIONCONFIGENTRY']._serialized_end=1199
  _globals['_DOMAIN_SLOTSENTRY']._serialized_start=500
  _globals['_DOMAIN_SLOTSENTRY']._serialized_end=544
  _globals['_DOMAIN_RESPONSESENTRY']._serialized_start=1247
  _globals['_DOMAIN_RESPONSESENTRY']._serialized_end=1295
  _globals['_DOMAIN_FORMSENTRY']._serialized_start=1297
  _globals['_DOMAIN_FORMSENTRY']._serialized_end=1341
  _globals['_WEBHOOKREQUEST']._serialized_start=1344
  _globals['_WEBHOOKREQUEST']._serialized_end=1513
  _globals['_WEBHOOKRESPONSE']._serialized_start=1515
  _globals['_WEBHOOKRESPONSE']._serialized_end=1611
  _globals['_ACTIONSERVERWEBHOOK']._serialized_start=1613
  _globals['_ACTIONSERVERWEBHOOK']._serialized_end=1724
# @@protoc_insertion_point(module_scope)
