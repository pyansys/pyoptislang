# Copyright (C) 2022 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"Module for testing server_queries.py"
import json

import pytest

from ansys.optislang.core.tcp import server_queries as sq

example_uid = "5cdfb20b-bef6-4412-9985-89f5ded5ee95"
example_dict = {"feature": "CAN_FINALIZE"}
example_hid = "0.1"
example_slot = "MySlot"
example_password = "otislang.-*123"


def test_actor_info():
    "Test actor_info."
    json_string = sq.actor_info(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_INFO", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"include_integrations_registered_locations": true, "include_log_messages": true} }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_info(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.actor_info()


def test_actor_internal_variables():
    "Test actor_internal_variables."
    json_string = sq.actor_internal_variables(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_INTERNAL_VARIABLES", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": { "include_reference_values": true } }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_internal_variables(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_actor_properties():
    "Test actor_properties."
    json_string = sq.actor_properties(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_PROPERTIES", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_properties(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.actor_properties()


def test_actor_registered_input_slots():
    "Test actor_registered_input_slots."
    json_string = sq.actor_registered_input_slots(uid=example_uid, include_reference_values=True)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_REGISTERED_INPUT_SLOTS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": { "include_reference_values": true } }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_registered_input_slots(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_actor_registered_output_slots():
    "Test actor_registered_output_slots."
    json_string = sq.actor_registered_output_slots(uid=example_uid, include_reference_values=True)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_REGISTERED_OUTPUT_SLOTS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": { "include_reference_values": true } }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_registered_output_slots(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_actor_registered_parameters():
    "Test actor_registered_parameters."
    json_string = sq.actor_registered_parameters(uid=example_uid, include_reference_values=True)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_REGISTERED_PARAMETERS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": { "include_reference_values": true } }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_registered_parameters(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_actor_registered_responses():
    "Test actor_registered_responses."
    json_string = sq.actor_registered_responses(uid=example_uid, include_reference_values=True)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_REGISTERED_RESPONSES", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": { "include_reference_values": true } }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_registered_responses(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_actor_states():
    "Test actor_states."
    json_string = sq.actor_states(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_STATES", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        ' "args": { "include_state_info": false } }',
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_states(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.actor_states()


def test_actor_status_info():
    "Test actor_status_info."
    json_string = sq.actor_status_info(uid=example_uid, hid=example_hid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_STATUS_INFO", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        ' "hid": "0.1", "args": {'
        ' "include_designs": true,'
        ' "include_design_values": true,'
        ' "include_non_scalar_design_values": false,'
        ' "include_algorithm_info": false } }',
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_status_info(uid=example_uid, hid=example_hid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.actor_status_info()
    with pytest.raises(TypeError):
        sq.actor_status_info(uid=example_uid)
    with pytest.raises(TypeError):
        sq.actor_status_info(hid=example_uid)


def test_actor_supports():
    "Test actor_supports."
    json_string = sq.actor_supports(uid=example_uid, feature_name="CAN_FINALIZE")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "ACTOR_SUPPORTS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        ' "args": { "feature": "CAN_FINALIZE" } }',
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.actor_supports(
        uid=example_uid, feature_name="CAN_FINALIZE", password=example_password
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.actor_supports()
    with pytest.raises(TypeError):
        sq.actor_supports(uid=example_uid)
    with pytest.raises(TypeError):
        sq.actor_supports(args=example_dict)


def test_available_input_locations():
    "Test available_input_locations."
    json_string = sq.available_input_locations(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "AVAILABLE_INPUT_LOCATIONS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.available_input_locations(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_available_nodes():
    "Test available_nodes."
    json_string = sq.available_nodes()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "AVAILABLE_NODES" }')
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.available_nodes(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_available_output_locations():
    "Test available_output_locations."
    json_string = sq.available_output_locations(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "AVAILABLE_OUTPUT_LOCATIONS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" }'
    )
    assert isinstance(json_string, str)
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.available_output_locations(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_basic_project_info():
    "Test basic_project_info."
    json_string = sq.basic_project_info()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "BASIC_PROJECT_INFO" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.basic_project_info(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.basic_project_info(rand_arg=example_uid)


def test_doe_size():
    "Test doe_size."
    json_string = sq.doe_size(uid=example_uid, sampling_type="fullfactorial", num_discrete_levels=2)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "DOE_SIZE", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"num_discrete_levels": 2, "sampling_type": "fullfactorial"}}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.doe_size(
        uid=example_uid,
        sampling_type="fullfactorial",
        num_discrete_levels=2,
        password=example_password,
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_full_project_status_info():
    "Test full_project_status_info."
    json_string = sq.full_project_status_info()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "FULL_PROJECT_STATUS_INFO", "args": {'
        ' "include_designs": true,'
        ' "include_design_values": true,'
        ' "include_non_scalar_design_values": false,'
        ' "include_algorithm_info": false,'
        ' "include_log_messages": true,'
        ' "include_integrations_registered_locations": true } }',
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.full_project_status_info(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.full_project_status_info(rand_arg=example_uid)


def test_full_project_tree():
    "Test full_project_tree."
    json_string = sq.full_project_tree()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "FULL_PROJECT_TREE" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.full_project_tree(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.full_project_tree(rand_arg=example_uid)


def test_full_project_tree_with_properties():
    "Test full_project_tree_with_properties."
    json_string = sq.full_project_tree_with_properties()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "FULL_PROJECT_TREE_WITH_PROPERTIES" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.full_project_tree_with_properties(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.full_project_tree_with_properties(rand_arg=example_uid)


def test_get_criteria():
    "Test get_criteria."
    json_string = sq.get_criteria(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"What": "GET_CRITERIA", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95"}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.get_criteria(
        uid=example_uid,
        password=example_password,
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_get_criterion():
    "Test get_criterion."
    json_string = sq.get_criterion(uid=example_uid, name="obj2")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"What": "GET_CRITERION", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
         "args": {"name": "obj2"}}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.get_criterion(
        uid=example_uid,
        name="obj2",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_get_designs():
    "Test get_designs."
    json_string = sq.get_designs(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"What": "GET_DESIGNS", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95"}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.get_designs(
        uid=example_uid,
        password=example_password,
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password


def test_hpc_licensing_forwarded_environment():
    "Test hpc_licensing_forwarded_environment."
    json_string = sq.hpc_licensing_forwarded_environment(uid=example_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "HPC_LICENSING_FORWARDED_ENVIRONMENT",'
        ' "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.hpc_licensing_forwarded_environment(uid=example_uid, password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.hpc_licensing_forwarded_environment()


def test_input_slot_value():
    "Test input slot value."
    json_string = sq.input_slot_value(uid=example_uid, hid=example_hid, slot_name="IDesign")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "INPUT_SLOT_VALUE", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        ' "args": {"legacy_design_format": false}, "hid": "0.1", "slot_name": "IDesign" }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.input_slot_value(
        uid=example_uid, hid=example_hid, slot_name="IDesign", password=example_password
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.input_slot_value()
    with pytest.raises(TypeError):
        sq.input_slot_value(uid=example_uid)
    with pytest.raises(TypeError):
        sq.input_slot_value(hid=example_hid)
    with pytest.raises(TypeError):
        sq.input_slot_value(slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.input_slot_value(hid=example_hid, slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.input_slot_value(uid=example_uid, slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.input_slot_value(uid=example_uid, hid=example_hid)


def test_output_slot_value():
    "Test output slot value."
    json_string = sq.output_slot_value(uid=example_uid, hid=example_hid, slot_name="ODesign")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "OUTPUT_SLOT_VALUE", "uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        ' "args": {"legacy_design_format": false}, "hid": "0.1", "slot_name": "ODesign" }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.output_slot_value(
        uid=example_uid, hid=example_hid, slot_name="ODesign", password=example_password
    )
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.output_slot_value()
    with pytest.raises(TypeError):
        sq.output_slot_value(uid=example_uid)
    with pytest.raises(TypeError):
        sq.output_slot_value(hid=example_hid)
    with pytest.raises(TypeError):
        sq.output_slot_value(slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.output_slot_value(hid=example_hid, slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.output_slot_value(uid=example_uid, slot_name=example_slot)
    with pytest.raises(TypeError):
        sq.output_slot_value(uid=example_uid, hid=example_hid)


def test_project_tree_systems():
    "Test project_tree_systems."
    json_string = sq.project_tree_systems()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "PROJECT_TREE_SYSTEMS" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.project_tree_systems(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.project_tree_systems(rand_arg=example_uid)


def test_project_tree_systems_with_properties():
    "Test project_tree_systems_with_properties."
    json_string = sq.project_tree_systems_with_properties()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "PROJECT_TREE_SYSTEMS_WITH_PROPERTIES" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.project_tree_systems_with_properties(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.project_tree_systems_with_properties(rand_arg=example_uid)


def test_server_info():
    "Test server_info."
    json_string = sq.server_info()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "SERVER_INFO" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.server_info(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.server_info(rand_arg=example_uid)


def test_server_is_alive():
    "Test server_is_alive."
    json_string = sq.server_is_alive()
    dictionary = json.loads(json_string)
    requiered_string = json.loads('{ "What": "SERVER_IS_ALIVE" }')
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.server_is_alive(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.server_is_alive(rand_arg=example_uid)


def test_systems_status_info():
    "Test server_status_info."
    json_string = sq.systems_status_info()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "What": "SYSTEMS_STATUS_INFO", "args": {'
        ' "include_designs": true,'
        ' "include_design_values": true,'
        ' "include_non_scalar_design_values": false,'
        ' "include_algorithm_info": false,'
        ' "include_log_messages": true,'
        ' "include_integrations_registered_locations": true } }',
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sq.systems_status_info(password=example_password)
    dictionary = json.loads(json_string)
    assert dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sq.systems_status_info(rand_arg=example_uid)
