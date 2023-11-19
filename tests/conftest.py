import os
import pathlib
import shutil

import pytest

from ansys.optislang.core import examples, utils


def pytest_addoption(parser):
    parser.addoption(
        "--local_osl",
        action="store_true",
        default=False,
        help="run tests with local optiSLang process",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--local_osl"):
        # --local_osl given in cli: run local optiSLang process
        skip_local_osl = pytest.mark.skip(reason="need --local_osl option to run")
        for item in items:
            if "local_osl" in item.keywords:
                item.add_marker(skip_local_osl)


@pytest.fixture
def executable():
    """Get path to the optiSLang executable.

    Returns
    -------
    str
        Path to the optiSLang executable.
    """
    osl_exec = utils.get_osl_exec()
    assert osl_exec is not None
    return osl_exec[1]


@pytest.fixture
def project_file(tmp_path):
    """Get path to the optiSLang project.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Builtin fixture to temporary directory unique to the test invocation.

    Returns
    -------
    str
        Path to the optiSLang project.
    """
    return os.path.join(tmp_path, "test.opf")


def get_server_info_file_path(project_file: str, server_info_file_name: str) -> str:
    """Get path to the server information file.

    Parameters
    ----------
    project_file : str
        Path to the project file.
    server_info_file_name : str
        Name of the server information file with file extension.

    Returns
    -------
    str
        Path to the server information file.
    """
    project_dir = os.path.dirname(project_file)
    project_name = pathlib.Path(project_file).stem
    return os.path.join(project_dir, project_name + ".opd", server_info_file_name)


@pytest.fixture
def server_info_file(project_file):
    """Get path to the server information file.

    Parameters
    ----------
    project_file : str
        Path to the project file.

    Returns
    -------
    str
        Path to the server information file.
    """
    info_file_name = "server_info.ini"
    return get_server_info_file_path(project_file, info_file_name)


@pytest.fixture
def tmp_example_project(tmp_path: pathlib.Path):
    """Access a temporary copy of an optiSLang project from the examples.

    Assumes the first example file to be an optiSLang project.
    """

    def _tmp_project(example: str):
        _, example_files = examples.get_files(example)
        if example_files is None:
            raise ValueError(f"No examples files for {example}")

        opf = example_files[0]
        if opf.suffix != ".opf":
            raise ValueError(f"Non-existing project file for example {example}")

        shutil.copy(opf, tmp_path)
        return tmp_path / opf.name

    return _tmp_project
