# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: rasa_sdk/grpc_py/action_webhook.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n%rasa_sdk/grpc_py/action_webhook.proto\x12\x15\x61\x63tion_server_webhook\x1a\x1cgoogle/protobuf/struct.proto\"\x10\n\x0e\x41\x63tionsRequest\";\n\x0f\x41\x63tionsResponse\x12(\n\x07\x61\x63tions\x18\x01 \x03(\x0b\x32\x17.google.protobuf.Struct\"\xb8\x03\n\x07Tracker\x12\x11\n\tsender_id\x18\x01 \x01(\t\x12&\n\x05slots\x18\x02 \x01(\x0b\x32\x17.google.protobuf.Struct\x12/\n\x0elatest_message\x18\x03 \x01(\x0b\x32\x17.google.protobuf.Struct\x12\'\n\x06\x65vents\x18\x04 \x03(\x0b\x32\x17.google.protobuf.Struct\x12\x0e\n\x06paused\x18\x05 \x01(\x08\x12\x1c\n\x0f\x66ollowup_action\x18\x06 \x01(\tH\x00\x88\x01\x01\x12\x43\n\x0b\x61\x63tive_loop\x18\x07 \x03(\x0b\x32..action_server_webhook.Tracker.ActiveLoopEntry\x12\x1f\n\x12latest_action_name\x18\x08 \x01(\tH\x01\x88\x01\x01\x12&\n\x05stack\x18\t \x03(\x0b\x32\x17.google.protobuf.Struct\x1a\x31\n\x0f\x41\x63tiveLoopEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x42\x12\n\x10_followup_actionB\x15\n\x13_latest_action_name\"K\n\x06Intent\x12\x14\n\x0cstring_value\x18\x01 \x01(\t\x12+\n\ndict_value\x18\x02 \x01(\x0b\x32\x17.google.protobuf.Struct\"K\n\x06\x45ntity\x12\x14\n\x0cstring_value\x18\x01 \x01(\t\x12+\n\ndict_value\x18\x02 \x01(\x0b\x32\x17.google.protobuf.Struct\"K\n\x06\x41\x63tion\x12\x14\n\x0cstring_value\x18\x01 \x01(\t\x12+\n\ndict_value\x18\x02 \x01(\x0b\x32\x17.google.protobuf.Struct\"\x9d\x03\n\x06\x44omain\x12\'\n\x06\x63onfig\x18\x01 \x01(\x0b\x32\x17.google.protobuf.Struct\x12/\n\x0esession_config\x18\x02 \x01(\x0b\x32\x17.google.protobuf.Struct\x12.\n\x07intents\x18\x03 \x03(\x0b\x32\x1d.action_server_webhook.Intent\x12/\n\x08\x65ntities\x18\x04 \x03(\x0b\x32\x1d.action_server_webhook.Entity\x12&\n\x05slots\x18\x05 \x01(\x0b\x32\x17.google.protobuf.Struct\x12*\n\tresponses\x18\x06 \x01(\x0b\x32\x17.google.protobuf.Struct\x12.\n\x07\x61\x63tions\x18\x07 \x03(\x0b\x32\x1d.action_server_webhook.Action\x12&\n\x05\x66orms\x18\x08 \x01(\x0b\x32\x17.google.protobuf.Struct\x12,\n\x0b\x65\x32\x65_actions\x18\t \x03(\x0b\x32\x17.google.protobuf.Struct\"\xd7\x01\n\x0eWebhookRequest\x12\x13\n\x0bnext_action\x18\x01 \x01(\t\x12\x11\n\tsender_id\x18\x02 \x01(\t\x12/\n\x07tracker\x18\x03 \x01(\x0b\x32\x1e.action_server_webhook.Tracker\x12-\n\x06\x64omain\x18\x04 \x01(\x0b\x32\x1d.action_server_webhook.Domain\x12\x0f\n\x07version\x18\x05 \x01(\t\x12\x1a\n\rdomain_digest\x18\x06 \x01(\tH\x00\x88\x01\x01\x42\x10\n\x0e_domain_digest\"f\n\x0fWebhookResponse\x12\'\n\x06\x65vents\x18\x01 \x03(\x0b\x32\x17.google.protobuf.Struct\x12*\n\tresponses\x18\x02 \x03(\x0b\x32\x17.google.protobuf.Struct2\xc3\x01\n\rActionService\x12X\n\x07Webhook\x12%.action_server_webhook.WebhookRequest\x1a&.action_server_webhook.WebhookResponse\x12X\n\x07\x41\x63tions\x12%.action_server_webhook.ActionsRequest\x1a&.action_server_webhook.ActionsResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'rasa_sdk.grpc_py.action_webhook_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _TRACKER_ACTIVELOOPENTRY._options = None
  _TRACKER_ACTIVELOOPENTRY._serialized_options = b'8\001'
  _globals['_ACTIONSREQUEST']._serialized_start=94
  _globals['_ACTIONSREQUEST']._serialized_end=110
  _globals['_ACTIONSRESPONSE']._serialized_start=112
  _globals['_ACTIONSRESPONSE']._serialized_end=171
  _globals['_TRACKER']._serialized_start=174
  _globals['_TRACKER']._serialized_end=614
  _globals['_TRACKER_ACTIVELOOPENTRY']._serialized_start=522
  _globals['_TRACKER_ACTIVELOOPENTRY']._serialized_end=571
  _globals['_INTENT']._serialized_start=616
  _globals['_INTENT']._serialized_end=691
  _globals['_ENTITY']._serialized_start=693
  _globals['_ENTITY']._serialized_end=768
  _globals['_ACTION']._serialized_start=770
  _globals['_ACTION']._serialized_end=845
  _globals['_DOMAIN']._serialized_start=848
  _globals['_DOMAIN']._serialized_end=1261
  _globals['_WEBHOOKREQUEST']._serialized_start=1264
  _globals['_WEBHOOKREQUEST']._serialized_end=1479
  _globals['_WEBHOOKRESPONSE']._serialized_start=1481
  _globals['_WEBHOOKRESPONSE']._serialized_end=1583
  _globals['_ACTIONSERVICE']._serialized_start=1586
  _globals['_ACTIONSERVICE']._serialized_end=1781
# @@protoc_insertion_point(module_scope)