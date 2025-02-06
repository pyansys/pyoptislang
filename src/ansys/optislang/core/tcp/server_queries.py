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

"""Module for generation of all server queries."""
import json
from typing import Any, Dict, Optional

QueryArgs = Dict[str, Any]

_ACTOR_INFO = "ACTOR_INFO"
_ACTOR_INTERNAL_VARIABLES = "ACTOR_INTERNAL_VARIABLES"
_ACTOR_PROPERTIES = "ACTOR_PROPERTIES"
_ACTOR_REGISTERED_INPUT_SLOTS = "ACTOR_REGISTERED_INPUT_SLOTS"
_ACTOR_REGISTERED_OUTPUT_SLOTS = "ACTOR_REGISTERED_OUTPUT_SLOTS"
_ACTOR_REGISTERED_PARAMETERS = "ACTOR_REGISTERED_PARAMETERS"
_ACTOR_REGISTERED_RESPONSES = "ACTOR_REGISTERED_RESPONSES"
_ACTOR_STATES = "ACTOR_STATES"
_ACTOR_STATUS_INFO = "ACTOR_STATUS_INFO"
_ACTOR_SUPPORTS = "ACTOR_SUPPORTS"
_AVAILABLE_INPUT_LOCATIONS = "AVAILABLE_INPUT_LOCATIONS"
_AVAILABLE_NODES = "AVAILABLE_NODES"
_AVAILABLE_OUTPUT_LOCATIONS = "AVAILABLE_OUTPUT_LOCATIONS"
_BASIC_PROJECT_INFO = "BASIC_PROJECT_INFO"
_DOE_SIZE = "DOE_SIZE"
_FULL_PROJECT_STATUS_INFO = "FULL_PROJECT_STATUS_INFO"
_FULL_PROJECT_TREE = "FULL_PROJECT_TREE"
_FULL_PROJECT_TREE_WITH_PROPERTIES = "FULL_PROJECT_TREE_WITH_PROPERTIES"
_GET_CRITERIA = "GET_CRITERIA"
_GET_CRITERION = "GET_CRITERION"
_GET_DESIGNS = "GET_DESIGNS"
_HPC_LICENSING_FORWARDED_ENVIRONMENT = "HPC_LICENSING_FORWARDED_ENVIRONMENT"
_INPUT_SLOT_VALUE = "INPUT_SLOT_VALUE"
_OUTPUT_SLOT_VALUE = "OUTPUT_SLOT_VALUE"
_PROJECT_TREE_SYSTEMS = "PROJECT_TREE_SYSTEMS"
_PROJECT_TREE_SYSTEMS_WITH_PROPERTIES = "PROJECT_TREE_SYSTEMS_WITH_PROPERTIES"
_RESULT_DESIGN = "RESULT_DESIGN"
_SERVER_INFO = "SERVER_INFO"
_SERVER_IS_ALIVE = "SERVER_IS_ALIVE"
_SYSTEMS_STATUS_INFO = "SYSTEMS_STATUS_INFO"
_FULL_SUBTREE_STATUS_INFO = "FULL_SUBTREE_STATUS_INFO"


def actor_info(
    uid: str,
    include_log_messages: bool = True,
    include_integrations_registered_locations: bool = True,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of actor_info query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_log_messages: bool, optional
        Whether actor log messages are to be included.
    include_integrations_registered_locations: bool, optional
        Whether registered integration locations are to be included.
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of actor_info query.
    """
    args: QueryArgs = {}
    args["include_log_messages"] = include_log_messages
    args["include_integrations_registered_locations"] = include_integrations_registered_locations
    return _to_json(_gen_query(what=_ACTOR_INFO, uid=uid, args=args, password=password))


def actor_internal_variables(
    uid: str, include_reference_values: bool = True, password: Optional[str] = None
) -> str:
    """Generate JSON string of actor_internal_variables query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_reference_values: bool, optional
        Whether reference values are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_internal_variables query.
    """
    return _to_json(
        _gen_query(
            what=_ACTOR_INTERNAL_VARIABLES,
            uid=uid,
            args={"include_reference_values": include_reference_values},
            password=password,
        )
    )


def actor_properties(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of actor_properties query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of actor_properties query.
    """
    return _to_json(_gen_query(what=_ACTOR_PROPERTIES, uid=uid, password=password))


def actor_registered_input_slots(
    uid: str, include_reference_values: bool = True, password: Optional[str] = None
) -> str:
    """Generate JSON string of actor_registered_input_slots query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_reference_values: bool, optional
        Whether reference values are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_registered_input_slots query.
    """
    return _to_json(
        _gen_query(
            what=_ACTOR_REGISTERED_INPUT_SLOTS,
            uid=uid,
            args={"include_reference_values": include_reference_values},
            password=password,
        )
    )


def actor_registered_output_slots(
    uid: str, include_reference_values: bool = True, password: Optional[str] = None
) -> str:
    """Generate JSON string of actor_registered_output_slots query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_reference_values: bool, optional
        Whether reference values are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_registered_output_slots query.
    """
    return _to_json(
        _gen_query(
            what=_ACTOR_REGISTERED_OUTPUT_SLOTS,
            uid=uid,
            args={"include_reference_values": include_reference_values},
            password=password,
        )
    )


def actor_registered_parameters(
    uid: str, include_reference_values: bool = True, password: Optional[str] = None
) -> str:
    """Generate JSON string of actor_registered_parameters query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_reference_values: bool, optional
        Whether reference values are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_registered_parameters query.
    """
    return _to_json(
        _gen_query(
            what=_ACTOR_REGISTERED_PARAMETERS,
            uid=uid,
            args={"include_reference_values": include_reference_values},
            password=password,
        )
    )


def actor_registered_responses(
    uid: str, include_reference_values: bool = True, password: Optional[str] = None
) -> str:
    """Generate JSON string of actor_registered_responses query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_reference_values: bool, optional
        Whether reference values are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_registered_responses query.
    """
    return _to_json(
        _gen_query(
            what=_ACTOR_REGISTERED_RESPONSES,
            uid=uid,
            args={"include_reference_values": include_reference_values},
            password=password,
        )
    )


def actor_states(
    uid: str,
    include_state_info: bool = False,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of actor_states query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_state_info: bool
        Include additional info for each state. Otherwise, only state IDs are returned.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_states query.
    """
    args: QueryArgs = {}
    args["include_state_info"] = include_state_info
    return _to_json(_gen_query(what=_ACTOR_STATES, uid=uid, args=args, password=password))


def actor_status_info(
    uid: str,
    hid: str,
    include_designs: bool = True,
    include_design_values: bool = True,
    include_non_scalar_design_values: bool = False,
    include_algorithm_info: bool = False,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of actor_status_info query.

    Parameters
    ----------
    uid: str
        Uid entry.
    hid: str
        Hid entry.
    include_designs: bool
        Include (result) designs in status info response.
    include_design_values: bool
        Include values in (result) designs.
    include_non_scalar_design_values: bool
        Include non scalar values in (result) designs.
    include_algorithm_info: bool
        Include algorithm result info in status info response.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of actor_status_info query.
    """
    args: QueryArgs = {}
    args["include_designs"] = include_designs
    args["include_design_values"] = include_design_values
    args["include_non_scalar_design_values"] = include_non_scalar_design_values
    args["include_algorithm_info"] = include_algorithm_info
    return _to_json(
        _gen_query(what=_ACTOR_STATUS_INFO, uid=uid, args=args, hid=hid, password=password)
    )


def actor_supports(uid: str, feature_name: str, password: Optional[str] = None) -> str:
    """Generate JSON string of actor_supports query.

    Parameters
    ----------
    uid: str
        Uid entry.
    feature_name: str
        Name of requested feature.
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of actor_supports query.
    """
    return _to_json(
        _gen_query(what=_ACTOR_SUPPORTS, uid=uid, args={"feature": feature_name}, password=password)
    )


def available_input_locations(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of available_input_locations query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of available_input_locations query.
    """
    return _to_json(
        _gen_query(
            what=_AVAILABLE_INPUT_LOCATIONS,
            uid=uid,
            password=password,
        )
    )


def available_nodes(password: Optional[str] = None) -> str:
    """Generate JSON string of available nodes query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of available nodes query.
    """
    return _to_json(_gen_query(what=_AVAILABLE_NODES, password=password))


def available_output_locations(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of available_output_locations query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of available_output_locations query.
    """
    return _to_json(
        _gen_query(
            what=_AVAILABLE_OUTPUT_LOCATIONS,
            uid=uid,
            password=password,
        )
    )


def basic_project_info(password: Optional[str] = None) -> str:
    """Generate JSON string of basic_project_info query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of basic_project_info query.
    """
    return _to_json(_gen_query(what=_BASIC_PROJECT_INFO, password=password))


def doe_size(
    uid: str, sampling_type: str, num_discrete_levels: int, password: Optional[str] = None
) -> str:
    """Generate JSON string of doe_size query.

    Parameters
    ----------
    uid: str
        Uid entry.
    sampling_type: str
        Sampling type.
    num_discrete_levels: int
        Number of discrete levels.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of doe_size query.
    """
    args: QueryArgs = {}
    args["sampling_type"] = sampling_type
    args["num_discrete_levels"] = num_discrete_levels
    return _to_json(
        _gen_query(
            what=_DOE_SIZE,
            uid=uid,
            args=args,
            password=password,
        )
    )


def full_project_status_info(
    include_designs: bool = True,
    include_design_values: bool = True,
    include_non_scalar_design_values: bool = False,
    include_algorithm_info: bool = False,
    include_log_messages: bool = True,
    include_integrations_registered_locations: bool = True,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of full_project_status_info query.

    Parameters
    ----------
    include_designs: bool
        Include (result) designs in status info response.
    include_design_values: bool
        Include values in (result) designs.
    include_non_scalar_design_values: bool
        Include non scalar values in (result) designs.
    include_algorithm_info: bool
        Include algorithm result info in status info response.
    include_log_messages: bool, optional
        Whether actor log messages are to be included.
    include_integrations_registered_locations: bool, optional
        Whether registered integration locations are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of full_project_status_info query.
    """
    args: QueryArgs = {}
    args["include_designs"] = include_designs
    args["include_design_values"] = include_design_values
    args["include_non_scalar_design_values"] = include_non_scalar_design_values
    args["include_algorithm_info"] = include_algorithm_info
    args["include_log_messages"] = include_log_messages
    args["include_integrations_registered_locations"] = include_integrations_registered_locations
    return _to_json(_gen_query(what=_FULL_PROJECT_STATUS_INFO, args=args, password=password))


def full_project_tree(password: Optional[str] = None) -> str:
    """Generate JSON string of full_project_tree query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of full_project_tree query.
    """
    return _to_json(_gen_query(what=_FULL_PROJECT_TREE, password=password))


def full_project_tree_with_properties(password: Optional[str] = None) -> str:
    """Generate JSON string of full_project_tree_with_properties query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of full_project_tree_with_properties query.
    """
    return _to_json(_gen_query(what=_FULL_PROJECT_TREE_WITH_PROPERTIES, password=password))


def full_subtree_status_info(
    uid: str,
    include_designs: bool = True,
    include_design_values: bool = True,
    include_non_scalar_design_values: bool = False,
    include_algorithm_info: bool = False,
    include_log_messages: bool = True,
    include_integrations_registered_locations: bool = True,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of full_subtree_status_info query.

    Parameters
    ----------
    uid: str
        Uid entry.
    include_designs: bool
        Include (result) designs in status info response.
    include_design_values: bool
        Include values in (result) designs.
    include_non_scalar_design_values: bool
        Include non scalar values in (result) designs.
    include_algorithm_info: bool
        Include algorithm result info in status info response.
    include_log_messages: bool, optional
        Whether actor log messages are to be included.
    include_integrations_registered_locations: bool, optional
        Whether registered integration locations are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of systems_status_info query.
    """
    args: QueryArgs = {}
    args["include_designs"] = include_designs
    args["include_design_values"] = include_design_values
    args["include_non_scalar_design_values"] = include_non_scalar_design_values
    args["include_algorithm_info"] = include_algorithm_info
    args["include_log_messages"] = include_log_messages
    args["include_integrations_registered_locations"] = include_integrations_registered_locations
    return _to_json(
        _gen_query(what=_FULL_SUBTREE_STATUS_INFO, uid=uid, args=args, password=password)
    )


def get_criteria(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of get_criteria query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of get_criteria query.
    """
    return _to_json(_gen_query(what=_GET_CRITERIA, uid=uid, password=password))


def get_criterion(uid: str, name: str, password: Optional[str] = None) -> str:
    """Generate JSON string of get_criterion query.

    Parameters
    ----------
    uid: str
        Uid entry.
    name: str
        Criterion name.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of get_criterion query.
    """
    return _to_json(
        _gen_query(what=_GET_CRITERION, uid=uid, args={"name": name}, password=password)
    )


def get_designs(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of get_designs query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of get_designs query.
    """
    return _to_json(_gen_query(what=_GET_DESIGNS, uid=uid, password=password))


def hpc_licensing_forwarded_environment(uid: str, password: Optional[str] = None) -> str:
    """Generate JSON string of hpc_licensing_forwarded_environment query.

    Parameters
    ----------
    uid: str
        Uid entry.
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of hpc_licensing_forwarded_environment query.
    """
    return _to_json(
        _gen_query(what=_HPC_LICENSING_FORWARDED_ENVIRONMENT, uid=uid, password=password)
    )


def input_slot_value(
    uid: str,
    hid: str,
    slot_name: str,
    legacy_design_format: bool = False,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of input_slot_value query.

    Parameters
    ----------
    uid: str
        Uid entry.
    hid: str
        Hid entry.
    slot_name: str
        Slot name entry.
    legacy_design_format: bool, optional
        Whether to use legacy format for designs and design container type slots.
        Defaults to false.

        .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of input_slot_value query.
    """
    return _to_json(
        _gen_query(
            what=_INPUT_SLOT_VALUE,
            uid=uid,
            hid=hid,
            slot_name=slot_name,
            args={"legacy_design_format": legacy_design_format},
            password=password,
        )
    )


def output_slot_value(
    uid: str,
    hid: str,
    slot_name: str,
    legacy_design_format: bool = False,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of output_slot_value query.

    Parameters
    ----------
    uid: str
        Uid entry.
    hid: str
        Hid entry.
    slot_name: str
        Slot name entry.
    legacy_design_format: bool, optional
        Whether to use legacy format for designs and design container type slots.
        Defaults to false.

        .. note:: Argument has effect for Ansys optiSLang version >= 25.2 only.

    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of output_slot_value query.
    """
    return _to_json(
        _gen_query(
            what=_OUTPUT_SLOT_VALUE,
            uid=uid,
            hid=hid,
            slot_name=slot_name,
            args={"legacy_design_format": legacy_design_format},
            password=password,
        )
    )


def project_tree_systems(password: Optional[str] = None) -> str:
    """Generate JSON string of project_tree_systems query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of project_tree_systems query.
    """
    return _to_json(_gen_query(what=_PROJECT_TREE_SYSTEMS, password=password))


def project_tree_systems_with_properties(password: Optional[str] = None) -> str:
    """Generate JSON string of project_tree_with_properties query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of project_tree_with_properties query.
    """
    return _to_json(_gen_query(what=_PROJECT_TREE_SYSTEMS_WITH_PROPERTIES, password=password))


def result_design(
    uid: str,
    design_id: str,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of result_design query.

    Parameters
    ----------
    uid: str
        Uid entry.
    design_id: str
        Design ID entry.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of result_design query.
    """
    return _to_json(
        _gen_query(what=_RESULT_DESIGN, uid=uid, design_id=design_id, password=password)
    )


def server_info(password: Optional[str] = None) -> str:
    """Generate JSON string of server_info query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of server_info query.
    """
    return _to_json(_gen_query(what=_SERVER_INFO, password=password))


def server_is_alive(password: Optional[str] = None) -> str:
    """Generate JSON string of server_is_alive query.

    Parameters
    ----------
    password : Optional[str], optional
        Password, by default ``None``.

    Returns
    -------
    str
        JSON string of server_is_alive query.
    """
    return _to_json(_gen_query(what=_SERVER_IS_ALIVE, password=password))


def systems_status_info(
    include_designs: bool = True,
    include_design_values: bool = True,
    include_non_scalar_design_values: bool = False,
    include_algorithm_info: bool = False,
    include_log_messages: bool = True,
    include_integrations_registered_locations: bool = True,
    password: Optional[str] = None,
) -> str:
    """Generate JSON string of systems_status_info query.

    Parameters
    ----------
    include_designs: bool
        Include (result) designs in status info response.
    include_design_values: bool
        Include values in (result) designs.
    include_non_scalar_design_values: bool
        Include non scalar values in (result) designs.
    include_algorithm_info: bool
        Include algorithm result info in status info response.
    include_log_messages: bool, optional
        Whether actor log messages are to be included.
    include_integrations_registered_locations: bool, optional
        Whether registered integration locations are to be included.
    password : Optional[str], optional
        Password. Defaults to ``None``.

    Returns
    -------
    str
        JSON string of systems_status_info query.
    """
    args: QueryArgs = {}
    args["include_designs"] = include_designs
    args["include_design_values"] = include_design_values
    args["include_non_scalar_design_values"] = include_non_scalar_design_values
    args["include_algorithm_info"] = include_algorithm_info
    args["include_log_messages"] = include_log_messages
    args["include_integrations_registered_locations"] = include_integrations_registered_locations
    return _to_json(_gen_query(what=_SYSTEMS_STATUS_INFO, args=args, password=password))


def _gen_query(
    what: str,
    password: Optional[str],
    uid: Optional[str] = None,
    hid: Optional[str] = None,
    args: Optional[QueryArgs] = None,
    slot_name: Optional[str] = None,
    design_id: Optional[str] = None,
) -> Dict:
    """Generate query in desired format.

    Parameters
    ----------
    what : str
        Command type.
    password: Optional[str], optional
        Password. Defaults to ``None``.
    uid : Optional[str], optional
        Uid entry. Defaults to ``None``.
    hid: Optional[str], optional
        Hid entry. Defaults to ``None``.
    args: Optional[QueryArgs], optional
        Dictionary of features, e.g. "feature": "FEATURE_NAME".
    slot_name: Optional[str], optional
        Slot name. Defaults to ``None``.
    design_id: Optional[str], optional
        Design ID. Defaults to ``None``.

    Returns
    -------
    Dict
        Dictionary with specified query inputs.
    """
    query: Dict[str, Any] = {}
    query["What"] = what
    if uid is not None:
        query["uid"] = uid
    if hid is not None:
        query["hid"] = hid
    if args is not None:
        query["args"] = args
    if slot_name is not None:
        query["slot_name"] = slot_name
    if design_id is not None:
        query["design_id"] = design_id
    if password is not None:
        query["Password"] = password
    return query


def _to_json(dict: Dict) -> str:
    """Convert dictionary to JSON.

    Parameters
    ----------
    dict : Dict
        Dictionary with specified query inputs.

    Returns
    -------
    str
        JSON string.
    """
    return json.dumps(dict, sort_keys=True, ensure_ascii=False)
