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

"Module for testing server_command.py"
import json

import pytest

from ansys.optislang.core.tcp import server_commands as sc

actor_uid = "5cdfb20b-bef6-4412-9985-89f5ded5ee95"
uid = "d2ab72dd-0d46-488a-aa05-0ddc19794c60"
uid_ = "8a79b28a-d79e-4a78-bf22-293f15c02b25"
hid = "0.1"
type_ = "sensitivity"
example_password = "otislang.-*123"
rand_arg = [1, "2", {3}]
path = "C:/samples_path/Project.opf"
script = "C:/samples_path/script.py"
result = "C:/samples_path/result.csv"
args_ = ["Sensi", "True"]
from_actor_uid = "3751b23c-3efb-459e-9b73-49cb4ae77e67"
to_actor_uid = "e849f1e9-75b0-4472-8447-d076b33c47bf"
parent_uid = "fa743edb-4e0b-4302-b962-f2a32119a110"
parameters = {"X1": 1.0, "X2": 1.0, "X3": 1.0}
local_location = {
    "split_path": {"head": "", "tail": "C:/samples_path/result.txt"},
    "base_path": "",
    "base_path_mode": "ABSOLUTE_PATH",
}
notifications = ["LOG_ERROR", "LOG_WARNING"]
value = {
    "split_path": {"head": "", "tail": "C:/samples_path/result.txt"},
    "base_path": "",
    "base_path_mode": "ABSOLUTE_PATH",
}
start_designs = [
    {
        "id": 1,
        "run_state": "done",
        "parameters": {
            "header": 0,
            "sequence": [{"First": "X1", "Second": "3.14"}, {"First": "X2", "Second": "-3.14"}],
        },
        "responses": {"header": 0, "sequence": [{"First": "Y", "Second": "-11.60"}]},
        "criteria": {
            "header": 0,
            "sequence": [{"First": "obj_Y", "Second": {"lhs": "", "rhs": "Y", "type": "min"}}],
        },
    }
]
parent_hwnd = "XXX"


def test_add_criterion():
    "Test add_criterion."
    # basic
    json_string = sc.add_criterion(
        actor_uid=actor_uid, criterion_type="max", expression="Y", name="obj2"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"criterion_type":"max", "expression": "Y", "limit": "", "name": "obj2"}, \
        "command": "ADD_CRITERION", "type": "builtin"}]}]}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())

    # with password
    json_string = sc.add_criterion(
        actor_uid=actor_uid,
        criterion_type="max",
        expression="Y",
        name="obj2",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_apply_wizzard():
    "Test apply_wizard."
    # basic
    json_string = sc.apply_wizard(actor_uid=actor_uid, type_=type_)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "APPLY_WIZARD",'
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
        '"args": { "type": "sensitivity" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.apply_wizard(
        actor_uid=actor_uid, type_=type_, use_existing_system=True, usage_mode="EXPERT"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "APPLY_WIZARD",'
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": { "type": "sensitivity",'
        '"use_existing_system": true, "usage_mode": "EXPERT" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.apply_wizard(actor_uid=actor_uid, type_=type_, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.apply_wizard()


def test_close():
    "Test close."
    # basic
    json_string = sc.close()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CLOSE" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.close(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.close(rand_arg=rand_arg)


def test_connect_nodes():
    "Test connect_nodes."
    # basic
    json_string = sc.connect_nodes(
        from_actor_uid=from_actor_uid,
        from_slot="OMDBPath",
        to_actor_uid=to_actor_uid,
        to_slot="IMDBPath",
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CONNECT_NODES", "args": '
        '{ "from_actor_uid": "3751b23c-3efb-459e-9b73-49cb4ae77e67", "from_slot": "OMDBPath", '
        '"to_actor_uid": "e849f1e9-75b0-4472-8447-d076b33c47bf", "to_slot": "IMDBPath", '
        '"skip_rename_slot": false } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.connect_nodes(
        from_actor_uid=from_actor_uid,
        from_slot="OMDBPath",
        to_actor_uid=to_actor_uid,
        to_slot="IMDBPath",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.connect_nodes()


def test_create_input_slot():
    "Test create_input_slot."
    # basic
    json_string = sc.create_input_slot(actor_uid=actor_uid, slot_name="MyInputSlot")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_INPUT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "slot_name": "MyInputSlot" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.create_input_slot(
        actor_uid=actor_uid, slot_name="MyInputSlot", type_hint="DESIGN_TYPE"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_INPUT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "slot_name": "MyInputSlot", "type_hint": "DESIGN_TYPE" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.create_input_slot(
        actor_uid=actor_uid, slot_name="MyInputSlot", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.create_input_slot(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.create_input_slot(slot_name="MyInputSlot")
    with pytest.raises(TypeError):
        sc.create_input_slot()


def test_create_node():
    "Test create_node."
    # basic
    json_string = sc.create_node(type_="Sensitivity", name="Sensi-System")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_NODE", '
        '"args": { "type": "Sensitivity", "name": "Sensi-System" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.create_node(
        type_="AnsysWorkbench", name="WB-Actor", parent_uid=parent_uid, design_flow="RECEIVE_SEND"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_NODE", "args": '
        '{ "type": "AnsysWorkbench", "name": "WB-Actor", "parent_uid": '
        '"fa743edb-4e0b-4302-b962-f2a32119a110","design_flow": "RECEIVE_SEND" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.create_node(
        type_="Sensitivity", name="Sensi-System", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.create_node(name="Sensi-System")


def test_create_output_slot():
    "Test create_output_slot."
    # basic
    json_string = sc.create_output_slot(actor_uid=actor_uid, slot_name="MyOutputSlot")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_OUTPUT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "slot_name": "MyOutputSlot" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.create_output_slot(
        actor_uid=actor_uid, slot_name="MyOutputSlot", type_hint="DESIGN_TYPE"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_OUTPUT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "slot_name": "MyOutputSlot", "type_hint": "DESIGN_TYPE" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.create_output_slot(
        actor_uid=actor_uid, slot_name="MyOutputSlot", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.create_output_slot(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.create_output_slot(slot_name="MyOutputSlot")
    with pytest.raises(TypeError):
        sc.create_output_slot()


def test_create_start_designs():
    "Test create_start_designs."
    # basic
    json_string = sc.create_start_designs(actor_uid=actor_uid, sampling_type="fullfactorial")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_START_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "sampling_type": "fullfactorial" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.create_start_designs(
        actor_uid=actor_uid, sampling_type="fullfactorial", number_of_levels=2
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_START_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "sampling_type": "fullfactorial", "number_of_levels": 2 } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.create_start_designs(
        actor_uid=actor_uid, sampling_type="fullfactorial", number_of_samples=2
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "CREATE_START_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "sampling_type": "fullfactorial", "number_of_samples": 2 } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.create_start_designs(
        actor_uid=actor_uid, sampling_type="fullfactorial", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.create_start_designs(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.create_start_designs(sampling_type="fullfactorial")
    with pytest.raises(TypeError):
        sc.create_start_designs(
            actor_uid=actor_uid,
            sampling_type="fullfactorial",
            number_of_samples=100,
            number_of_levels=2,
        )
    with pytest.raises(TypeError):
        sc.create_start_designs()


def test_disconnect_slot():
    "Test disconnect_slot."
    # first option
    json_string = sc.disconnect_slot(
        actor_uid=actor_uid, slot_name="MyInputSlot", direction="sdInputs"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "DISCONNECT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "slot_name": "MyInputSlot", "direction": "sdInputs" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # second option
    json_string = sc.disconnect_slot(
        actor_uid=actor_uid, slot_name="MyOutputSlot", direction="sdOutputs"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "DISCONNECT_SLOT", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": { "slot_name": '
        '"MyOutputSlot", "direction": "sdOutputs" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.disconnect_slot(
        actor_uid=actor_uid,
        slot_name="MyInputSlot",
        direction="sdInputs",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.disconnect_slot(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.disconnect_slot(actor_uid=actor_uid, slot_name="MyInputSlot")
    with pytest.raises(TypeError):
        sc.disconnect_slot(actor_uid=actor_uid, direction="sdInputs")
    with pytest.raises(TypeError):
        sc.disconnect_slot(slot_name="MyInputSlot", direction="sdInputs")
    with pytest.raises(TypeError):
        sc.disconnect_slot()


def test_evaluate_design():
    "Test aevaluate_design."
    # basic
    json_string = sc.evaluate_design(parameters=parameters)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "EVALUATE_DESIGN", '
        '"args": { "parameters": { "X1": 1.0, "X2": 1.0, "X3": 1.0 } } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.evaluate_design(parameters=parameters, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.evaluate_design()


def test_export_designs():
    "Test export_designs."
    # basic
    json_string = sc.export_designs(actor_uid=actor_uid, path=result)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "EXPORT_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "path": "C:/samples_path/result.csv"} } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.export_designs(
        actor_uid=actor_uid, path=result, format="csv", csv_separator="\t"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "EXPORT_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": '
        '{ "path": "C:/samples_path/result.csv", '
        r'"format": "csv", "csv_separator": "\t" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.export_designs(actor_uid=actor_uid, path=result, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.export_designs(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.export_designs(path=path)
    with pytest.raises(TypeError):
        sc.export_designs()


def test_finalize():
    "Test finalize."
    # basic
    json_string = sc.finalize(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "FINALIZE", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.finalize(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.finalize()


def test_link_registered_file():
    "Test link_registered_file."
    # basic
    json_string = sc.link_registered_file(actor_uid=actor_uid, uid=uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"LINK_REGISTERED_FILE", "actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", '
        '"args": { "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.link_registered_file(actor_uid=actor_uid, uid=uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.link_registered_file(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.link_registered_file(uid=uid)
    with pytest.raises(TypeError):
        sc.link_registered_file()


def test_load():
    "Test ``load``."
    # basic
    json_string = sc.load(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "LOAD", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.load(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.load()


def test_new():
    "Test new."
    # basic
    json_string = sc.new()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "NEW" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.new(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.new(rand_arg=rand_arg)


def test_open():
    "Test open."
    # basic
    json_string = sc.open(path=path, do_force=True, do_restore=False, do_reset=False)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "OPEN", "args":'
        '{ "path": "C:/samples_path/Project.opf", "do_force": true, "do_restore": false,'
        '"do_reset": false } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.open(
        path=path, do_force=True, do_restore=False, do_reset=False, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.open()


def test_pause():
    "Test pause."
    # basic
    json_string = sc.pause()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "PAUSE" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.pause(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.finalize(rand_arg=rand_arg)


def test_reevaluate_state():
    "Test reevaluate_state."
    # basic
    json_string = sc.reevaluate_state(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REEVALUATE_STATE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.reevaluate_state(actor_uid=actor_uid, hid=hid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REEVALUATE_STATE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "hid": "0.1" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.reevaluate_state(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.reevaluate_state()


def test_refresh_listener_registration():
    "Test refresh_listener_registration."
    # basic
    json_string = sc.refresh_listener_registration(uid=uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"REFRESH_LISTENER_REGISTRATION", "args":'
        '{ "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.refresh_listener_registration(uid=uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.refresh_listener_registration()


def test_register_file():
    "Test register_file."
    # basic
    json_string = sc.register_file(ident="File 42", action="Send", local_location=local_location)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REGISTER_FILE", '
        '"args": { "ident": "File 42", "action": "Send", "local_location": { "split_path": '
        '{"head": "", "tail": "C:/samples_path/result.txt" }, "base_path": "", '
        '"base_path_mode": "ABSOLUTE_PATH" } } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_file(
        ident="File42", action="Send", local_location=local_location, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_file(rand_arg=rand_arg)


def test_register_listener():
    "Test register_listener."
    # option 1
    json_string = sc.register_listener(id="123456")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REGISTER_LISTENER", '
        '"args": { "id": "123456" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # option 2
    json_string = sc.register_listener(host="127.0.0.1", port=5330)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REGISTER_LISTENER", '
        '"args": { "host": "127.0.0.1", "port": 5330 } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.register_listener(
        host="127.0.0.1",
        port=5330,
        timeout=30000,
        notifications=notifications,
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REGISTER_LISTENER", '
        '"args": { "host": "127.0.0.1", "port": 5330, "timeout": 30000, "notifications": '
        '["LOG_ERROR", "LOG_WARNING"] } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_listener(id="123456", password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_listener(id="123456", host="127.0.0.1", port=5330)
    with pytest.raises(TypeError):
        sc.register_listener(id="123456", port=5330)
    with pytest.raises(TypeError):
        sc.register_listener(host="127.0.0.1")
    with pytest.raises(TypeError):
        sc.register_listener()


def test_register_location_as_input_slot():
    "Test ``register_location_as_input_slot``."
    # basic
    json_string = sc.register_location_as_input_slot(
        actor_uid=actor_uid, location={}, name="my_name", reference_value=42.0
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        (
            '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
            '"args": {"location": {}, "name": "my_name", "reference_value": 42.0},'
            '"command": "REGISTER_LOCATION_AS_INPUT_SLOT", "type": "builtin"}]}]}'
        )
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_location_as_input_slot(
        actor_uid=actor_uid, location={}, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_location_as_input_slot()


def test_register_location_as_internal_variable():
    "Test ``register_location_as_internal_variable``."
    # basic
    json_string = sc.register_location_as_internal_variable(
        actor_uid=actor_uid, location={}, name="my_name", reference_value=42.0
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        (
            '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
            '"args": {"location": {}, "name": "my_name", "reference_value": 42.0},'
            '"command": "REGISTER_LOCATION_AS_INTERNAL_VARIABLE", "type": "builtin"}]}]}'
        )
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_location_as_internal_variable(
        actor_uid=actor_uid, location={}, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_location_as_internal_variable()


def test_register_location_as_output_slot():
    "Test ``register_location_as_output_slot``."
    # basic
    json_string = sc.register_location_as_output_slot(
        actor_uid=actor_uid, location={}, name="my_name", reference_value=42.0
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        (
            '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
            '"args": {"location": {}, "name": "my_name", "reference_value": 42.0},'
            '"command": "REGISTER_LOCATION_AS_OUTPUT_SLOT", "type": "builtin"}]}]}'
        )
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_location_as_output_slot(
        actor_uid=actor_uid, location={}, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_location_as_output_slot()


def test_register_location_as_parameter():
    "Test ``register_location_as_parameter``."
    # basic
    json_string = sc.register_location_as_parameter(
        actor_uid=actor_uid, location={}, name="my_name", reference_value=42.0
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        (
            '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
            '"args": {"location": {}, "name": "my_name", "reference_value": 42.0},'
            '"command": "REGISTER_LOCATION_AS_PARAMETER", "type": "builtin"}]}]}'
        )
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_location_as_parameter(
        actor_uid=actor_uid, location={}, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_location_as_parameter()


def test_register_locations_as_parameter():
    "Test register_locations_as_parameter."
    # basic
    json_string = sc.register_locations_as_parameter(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"REGISTER_LOCATIONS_AS_PARAMETER", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_locations_as_parameter(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_locations_as_parameter()


def test_register_location_as_response():
    "Test ``register_location_as_response``."
    # basic
    json_string = sc.register_location_as_response(
        actor_uid=actor_uid, location={}, name="my_name", reference_value=42.0
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        (
            '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95",'
            '"args": {"location": {}, "name": "my_name", "reference_value": 42.0},'
            '"command": "REGISTER_LOCATION_AS_RESPONSE", "type": "builtin"}]}]}'
        )
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_location_as_response(
        actor_uid=actor_uid, location={}, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_location_as_response()


def test_register_locations_as_response():
    "Test register_locations_as_response."
    # basic
    json_string = sc.register_locations_as_response(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"REGISTER_LOCATIONS_AS_RESPONSE", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.register_locations_as_response(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.register_locations_as_response()


def test_remove_criteria():
    "Test remove_criteria."
    # basic
    json_string = sc.remove_criteria(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "command": "REMOVE_CRITERIA", "type": "builtin"}]}]}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.remove_criteria(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_remove_criterion():
    "Test remove_criterion."
    # basic
    json_string = sc.remove_criterion(actor_uid=actor_uid, name="obj2")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"name": "obj2"}, "command": "REMOVE_CRITERION", "type": "builtin"}]}]}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.remove_criterion(actor_uid=actor_uid, name="obj2", password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_remove_node():
    "Test remove_node."
    # basic
    json_string = sc.remove_node(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "REMOVE_NODE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.remove_node(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.remove_node()


def test_re_register_locations_as_parameter():
    "Test re_register_locations_as_parameter."
    # basic
    json_string = sc.re_register_locations_as_parameter(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"RE_REGISTER_LOCATIONS_AS_PARAMETER", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.re_register_locations_as_parameter(
        actor_uid=actor_uid, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.re_register_locations_as_parameter()


def test_re_register_locations_as_response():
    "Test re_register_locations_as_response."
    # basic
    json_string = sc.re_register_locations_as_response(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"RE_REGISTER_LOCATIONS_AS_RESPONSE", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.re_register_locations_as_response(
        actor_uid=actor_uid, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.re_register_locations_as_response()


def test_reset():
    "Test reset."
    # basic
    json_string = sc.reset()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RESET" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.reset(actor_uid=actor_uid, hid=hid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RESET", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95", "hid": "0.1" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.reset(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_restart():
    "Test restart."
    # basic
    json_string = sc.restart()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RESTART" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.restart(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_resume():
    "Test restart."
    # basic
    json_string = sc.resume()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RESUME" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.resume(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_run_python_script():
    "Test run python script."
    # basic
    json_string = sc.run_python_script(script=script)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RUN_PYTHON_SCRIPT",'
        '"args": { "script": "C:/samples_path/script.py" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.run_python_script(script=script, args_=args_)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "RUN_PYTHON_SCRIPT",'
        '"args": { "script": "C:/samples_path/script.py", "args": [ "Sensi", "True" ] } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.run_python_script(script=script, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.run_python_script()


def test_run_registered_files_actions():
    "Test run_registered_files_actions."
    # basic
    json_string = sc.run_registered_files_actions()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"RUN_REGISTERED_FILES_ACTIONS" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with optional values
    json_string = sc.run_registered_files_actions(uid=uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"RUN_REGISTERED_FILES_ACTIONS", "args": '
        '{ "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.run_registered_files_actions(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_save():
    "Test save."
    # basic
    json_string = sc.save()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SAVE" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.save(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.save(rand_arg=rand_arg)


def test_save_as():
    "Test save as."
    # basic
    json_string = sc.save_as(path=path, do_force=True, do_restore=False, do_reset=False)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SAVE_AS", "args":'
        '{ "path": "C:/samples_path/Project.opf", "do_force": true, "do_restore": false,'
        '"do_reset": false } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.save_as(
        path=path, do_force=True, do_restore=False, do_reset=False, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.save_as()


def test_save_copy():
    "Test save copy."
    # basic
    json_string = sc.save_copy(path=path)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SAVE_COPY",'
        '"args": { "path": "C:/samples_path/Project.opf" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.save_copy(path=path, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.save_copy()


def test_set_actor_property():
    "Test set_actor_property."
    # basic
    json_string = sc.set_actor_property(actor_uid=actor_uid, name="MaxParallel", value="32")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_ACTOR_PROPERTY", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": { "name": "MaxParallel", '
        '"value": "32" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_actor_property(
        actor_uid=actor_uid, name="MaxParallel", value="32", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_actor_property(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.set_actor_property(actor_uid=actor_uid, name="MaxParallel")
    with pytest.raises(TypeError):
        sc.set_actor_property(actor_uid=actor_uid, value="32")
    with pytest.raises(TypeError):
        sc.set_actor_property(name="MaxParallel", value="32")


def test_set_actor_setting():
    "Test set_actor_setting."
    # basic
    json_string = sc.set_actor_setting(
        actor_uid=actor_uid, name="maximum_designs_to_validate", value="5"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SET_ACTOR_SETTING", "actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", '
        '"args": { "name": "maximum_designs_to_validate", "value": "5" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_actor_setting(
        actor_uid=actor_uid,
        name="maximum_designs_to_validate",
        value="5",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_actor_setting(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.set_actor_setting(actor_uid=actor_uid, name="maximum_designs_to_validate")
    with pytest.raises(TypeError):
        sc.set_actor_setting(actor_uid=actor_uid, value="5")
    with pytest.raises(TypeError):
        sc.set_actor_setting(name="maximum_designs_to_validate", value="5")


def test_set_actor_state_property():
    "Test set_actor_state_property."
    # basic
    json_string = sc.set_actor_state_property(
        actor_uid=actor_uid, name="stop_after_execution", value="true"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SET_ACTOR_STATE_PROPERTY", "actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", '
        '"args": { "name": "stop_after_execution", "value": "true" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_actor_state_property(
        actor_uid=actor_uid, name="stop_after_execution", value="true", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_actor_state_property(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.set_actor_state_property(actor_uid=actor_uid, name="stop_after_execution")
    with pytest.raises(TypeError):
        sc.set_actor_state_property(actor_uid=actor_uid, value="true")
    with pytest.raises(TypeError):
        sc.set_actor_state_property(name="stop_after_execution", value="true")


def test_set_criterion_property():
    "Test set_criterion_property."
    # basic
    json_string = sc.set_criterion_property(
        actor_uid=actor_uid, criterion_name="obj2", name="type", value="min"
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"criterion_name": "obj2", "name": "type", "value": "min"}, \
        "command": "SET_CRITERION_PROPERTY", "type": "builtin"}]}]}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_criterion_property(
        actor_uid=actor_uid,
        criterion_name="obj2",
        name="type",
        value="min",
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_set_designs():
    "Test set_designs."
    # basic
    designs = [
        {
            "hid": "0.1",
            "responses": [{"name": "res1", "value": 1.0}],
        },
        {
            "hid": "0.2",
            "responses": [{"name": "res1", "value": 2.0}],
        },
    ]
    json_string = sc.set_designs(actor_uid=actor_uid, designs=designs)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{"projects": [{"commands": [{"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", \
        "args": {"designs": [{"hid": "0.1", "responses": [{"name": "res1", "value": 1.0}]}, \
        {"hid": "0.2","responses": [{"name": "res1", "value": 2.0}]}]}, \
        "command": "SET_DESIGNS","type": "builtin"}]}]}'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_designs(
        actor_uid=actor_uid,
        designs=designs,
        password=example_password,
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password


def test_set_placeholder_value():
    "Test set_placeholder_value."
    # basic
    json_string = sc.set_placeholder_value(name="model_name", value="model1")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_PLACEHOLDER_VALUE", '
        '"args": { "name": "model_name", "value": "model1" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_placeholder_value(
        name="model_name", value="model1", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_placeholder_value(name="model_name")
    with pytest.raises(TypeError):
        sc.set_placeholder_value(value="model1")
    with pytest.raises(TypeError):
        sc.set_placeholder_value()


def test_set_project_setting():
    "Test set_project_setting."
    # basic
    json_string = sc.set_project_setting(name="number_of_message_queue_threads", value="64")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_PROJECT_SETTING", '
        '"args": { "name": "number_of_message_queue_threads", "value": "64" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_project_setting(
        name="number_of_message_queue_threads", value="64", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_project_setting(name="number_of_message_queue_threads")
    with pytest.raises(TypeError):
        sc.set_project_setting(value="64")
    with pytest.raises(TypeError):
        sc.set_project_setting()


def test_set_registered_file_value():
    "Test set_registered_file_value."
    # opt1
    json_string = sc.set_registered_file_value(uid=uid, name="embedded", value="true")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SET_REGISTERED_FILE_VALUE", "args": { "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60", '
        '"name": "embedded", "value": "true" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # opt2
    json_string = sc.set_registered_file_value(uid=uid, name="local_location", value=value)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SET_REGISTERED_FILE_VALUE", "args": { "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60", '
        '"name": "local_location", "value": '
        '{ "split_path": {"head": "", "tail": "C:/samples_path/result.txt" }, "base_path": "", '
        '"base_path_mode": "ABSOLUTE_PATH" } } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_registered_file_value(
        uid=uid, name="embedded", value="true", password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_registered_file_value(uid=uid, name="embedded")
    with pytest.raises(TypeError):
        sc.set_registered_file_value(uid=uid, value="true")
    with pytest.raises(TypeError):
        sc.set_registered_file_value(name="embedded", value="true")


def test_set_start_designs():
    "Test set_start_designs."
    # opt1
    json_string = sc.set_start_designs(actor_uid=actor_uid, start_designs=start_designs)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_START_DESIGNS", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "args": { "start_designs": '
        '[ { "id": 1, "run_state": "done", "parameters": { "header": 0, "sequence": '
        '[ { "First": "X1", "Second": "3.14" }, { "First": "X2", "Second": "-3.14" } ] }, '
        '"responses": { "header": 0, "sequence": [ { "First": "Y", "Second": "-11.60" } ] }, '
        '"criteria": { "header": 0, "sequence": [ { "First": "obj_Y", "Second": '
        '{ "lhs": "", "rhs": "Y", "type": "min" } } ] } } ] } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_start_designs(
        actor_uid=actor_uid, start_designs=start_designs, password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_start_designs(actor_uid=actor_uid)
    with pytest.raises(TypeError):
        sc.set_start_designs(start_designs=start_designs)
    with pytest.raises(TypeError):
        sc.set_start_designs()


def test_set_succeeded_state():
    "Test set_succeeded_state."
    # basic
    json_string = sc.set_succeeded_state(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_SUCCEEDED_STATE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.set_succeeded_state(actor_uid=actor_uid, hid=hid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SET_SUCCEEDED_STATE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", "hid": "0.1" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.set_succeeded_state(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.set_succeeded_state()
    with pytest.raises(TypeError):
        sc.set_succeeded_state(hid=hid)


def test_show_dialog():
    "Test show_dialog."
    # basic 1
    json_string = sc.show_dialog(type_="help")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SHOW_DIALOG", '
        '"args": { "type": "help" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # basic 2
    json_string = sc.show_dialog(type_="project_settings")
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SHOW_DIALOG", "args": '
        '{ "type": "project_settings" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.show_dialog(type_="project_settings", usage_mode="EXPERT", parent_hwnd="XXX")
    dictionary = json.loads(json_string)
    dictionary["parent_hwnd"] = "XXX"
    dictionary["usage_mode"] = "EXPERT"
    # with password
    json_string = sc.show_dialog(type_="help", password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.show_dialog(type_="random")
    with pytest.raises(TypeError):
        sc.show_dialog()


def test_show_node_dialog():
    "Test show_node_dialog."
    # basic
    json_string = sc.show_node_dialog(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SHOW_NODE_DIALOG", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optional
    json_string = sc.show_node_dialog(
        actor_uid=actor_uid, blocking="true", type_="help", usage_mode="EXPERT", parent_hwnd="XXX"
    )
    dictionary = json.loads(json_string)
    dictionary["blocking"] = "true"
    dictionary["type"] = "help"
    dictionary["parent_hwnd"] = "XXX"
    dictionary["usage_mode"] = "EXPERT"
    # with password
    json_string = sc.show_node_dialog(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.show_node_dialog(blocking="true", type_="help", usage_mode="EXPERT", parent_hwnd="XXX")
    with pytest.raises(TypeError):
        sc.show_node_dialog()


def test_shutdown():
    "Test shutdown."
    # basic
    json_string = sc.shutdown()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "SHUTDOWN", '
        '"args": { "force": false } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.shutdown(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.shutdown(rand_arg=rand_arg)


def test_shutdown_when_finished():
    "Test shutdown when finished."
    # basic
    json_string = sc.shutdown_when_finished()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin",'
        '"command": "SHUTDOWN_WHEN_FINISHED" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.shutdown_when_finished(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.shutdown_when_finished(rand_arg=rand_arg)


def test_start():
    "Test start."
    # basic
    json_string = sc.start()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "START" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.start(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.start(rand_arg=rand_arg)


def test_stop():
    "Test stop."
    # basic
    json_string = sc.stop()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "STOP" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.stop(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.stop(rand_arg=rand_arg)


def test_stop_gently():
    "Test stop gently."
    # basic
    json_string = sc.stop_gently()
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "STOP_GENTLY" } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.stop_gently(password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.stop_gently(rand_arg=rand_arg)


def test_subscribe_for_push_notifications():
    "Test subscribe_for_push_notifications."
    # basic
    json_string = sc.subscribe_for_push_notifications(uid=uid_, notifications=["ALL"])
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SUBSCRIBE_FOR_PUSH_NOTIFICATIONS", "args": '
        '{ "uid": "8a79b28a-d79e-4a78-bf22-293f15c02b25", "notifications": ["ALL"] } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # another notifications
    json_string = sc.subscribe_for_push_notifications(
        uid=uid_, notifications=["LOG_INFO", "ACTOR_ACTIVE_CHANGED", "CHECK_FAILED"]
    )
    dictionary = json.loads(json_string)
    dictionary["notifications"] = ["LOG_INFO", "ACTOR_ACTIVE_CHANGED", "CHECK_FAILED"]
    # optional
    json_string = sc.subscribe_for_push_notifications(
        uid=uid_, notifications=["ALL"], node_types=["Sensitivity", "AnsysWorkbench"]
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"SUBSCRIBE_FOR_PUSH_NOTIFICATIONS", "args": { "uid": '
        '"8a79b28a-d79e-4a78-bf22-293f15c02b25", "notifications": '
        '["ALL"], "node_types": ["Sensitivity", "AnsysWorkbench"] } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.subscribe_for_push_notifications(
        uid=uid_, notifications=["ALL"], password=example_password
    )
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.subscribe_for_push_notifications(uid=uid_)
    with pytest.raises(TypeError):
        sc.subscribe_for_push_notifications(notifications=["ALL"])
    with pytest.raises(TypeError):
        sc.subscribe_for_push_notifications(uid=uid_, notifications=["RANDOM"])
    with pytest.raises(TypeError):
        sc.subscribe_for_push_notifications(uid=uid_, notifications=["LOG_INFO", "RANDOM"])


def test_unlink_registered_file():
    "Test unlink_registered_file."
    # basic
    json_string = sc.unlink_registered_file(actor_uid=actor_uid, uid=uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "UNLINK_REGISTERED_FILE", '
        '"actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", '
        '"args": { "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.unlink_registered_file(actor_uid=actor_uid, uid=uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.unlink_registered_file(uid=uid)
    with pytest.raises(TypeError):
        sc.unlink_registered_file(actor_uid=actor_uid)


def test_unregister_file():
    "Test unregister_file."
    # basic
    json_string = sc.unregister_file(uid=uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "UNREGISTER_FILE", '
        '"args": { "uid": "d2ab72dd-0d46-488a-aa05-0ddc19794c60" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.unregister_file(uid=uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.unregister_file()


def test_unregister_listener():
    "Test unregister_listener."
    # basic
    json_string = sc.unregister_listener(uid=uid_)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": "UNREGISTER_LISTENER", '
        '"args": { "uid": "8a79b28a-d79e-4a78-bf22-293f15c02b25" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.unregister_listener(uid=uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.unregister_listener()


def test_write_monitoring_database():
    "Test write_monitoring_database."
    # basic
    json_string = sc.write_monitoring_database(actor_uid=actor_uid)
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"WRITE_MONITORING_DATABASE", "actor_uid": '
        '"5cdfb20b-bef6-4412-9985-89f5ded5ee95"} ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # optionals
    json_string = sc.write_monitoring_database(
        actor_uid=actor_uid, path="C:/samples_path/result.omdb", hid=hid
    )
    dictionary = json.loads(json_string)
    requiered_string = json.loads(
        '{ "projects": [ { "commands": [ { "type": "builtin", "command": '
        '"WRITE_MONITORING_DATABASE", "actor_uid": "5cdfb20b-bef6-4412-9985-89f5ded5ee95", '
        '"args": { "path": "C:/samples_path/result.omdb", "hid": "0.1" } } ] } ] }'
    )
    assert type(json_string) == str
    assert sorted(dictionary.items()) == sorted(requiered_string.items())
    # with password
    json_string = sc.write_monitoring_database(actor_uid=actor_uid, password=example_password)
    dictionary = json.loads(json_string)
    dictionary["Password"] == example_password
    with pytest.raises(TypeError):
        sc.write_monitoring_database(path="C:/samples_path/result.omdb", hid=hid)
    with pytest.raises(TypeError):
        sc.write_monitoring_database()
