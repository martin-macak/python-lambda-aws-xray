import logging
import pytest
import docker
from docker.models.images import Image as DockerImage
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


@dataclass
class TestContext:
    client: docker.DockerClient
    layer_path: Path
    image: DockerImage


@pytest.fixture(scope="session")
def test_container(request) -> Generator[TestContext, None, None]:
    import docker
    import zipfile
    import tempfile
    import shutil

    project_root = _find_project_root()
    layer_zip = project_root / "dist" / "layer.zip"
    assert (
        layer_zip.exists()
    ), f"Layer zip file does not exist: {layer_zip}, run make before running this test"

    client = docker.from_env()

    with tempfile.TemporaryDirectory(delete=False) as temp_dir:
        temp_path = Path(temp_dir)

        def fin_temp_dir():
            # force delete the temp directory
            try:
                shutil.rmtree(temp_dir)
            finally:
                pass

        request.addfinalizer(fin_temp_dir)

        # Unzip the layer.zip into temp directory
        with zipfile.ZipFile(layer_zip, "r") as zip_ref:
            zip_ref.extractall(temp_path)

        # Build docker image from Dockerfile
        dockerfile_path = Path(__file__).parent / "Dockerfile"
        test_dir = Path(__file__).parent

        logger.debug(
            f"Building image from {test_dir} with Dockerfile {dockerfile_path}"
        )
        image, _ = client.images.build(
            path=str(test_dir), dockerfile=str(dockerfile_path), tag="xray-test:latest"
        )
        logger.debug(f"Image built: {image.id}")

        # Check if bin directory exists in extracted layer
        layer_bin_path = temp_path / "bin"

        # Clean up image
        def fin_2():
            logger.debug("Removing image")
            client.images.remove(image.id, force=True)
            logger.debug("Image removed")

        request.addfinalizer(fin_2)

        yield TestContext(
            client=client,
            layer_path=layer_bin_path,
            image=image,
        )


def test_aws_lambda_exec_wrapper(request, test_container: TestContext):
    """
    This test checks that AWS_LAMBDA_EXEC_WRAPPER really works.
    Setting it to non-existing path should cause the container to exit with code 127.
    """

    container = test_container.client.containers.run(
        test_container.image.id,
        detach=True,
        environment={
            "AWS_LAMBDA_EXEC_WRAPPER": "/this/does/not/exist",
            "AWS_LAMBDA_RUNTIME_API": "dummy",
        },
    )

    def fin_container():
        try:
            container.stop()
            container.wait()
            container.remove()
        finally:
            pass

    request.addfinalizer(fin_container)

    try:
        container.wait(timeout=1)
    except Exception as e:
        logger.warning(f"Container wait timed out after 5 seconds: {e}")
        assert False, f"Container wait timed out after 5 seconds: {e}"

    container.reload()
    exit_code = container.attrs["State"]["ExitCode"]
    assert exit_code == 127, f"Container exited with non-zero code: {exit_code}"


def test_sitecustomize(request, test_container: TestContext):
    # Test that the layer contains the required components
    assert test_container.layer_path.exists(), "Layer path should exist"
    
    # Check that bootstrap script exists and has correct content
    bootstrap_path = test_container.layer_path / "bootstrap"
    assert bootstrap_path.exists(), "Bootstrap script should exist"
    
    bootstrap_content = bootstrap_path.read_text()
    assert "TEST_AND_EXIT" in bootstrap_content, "Bootstrap should contain TEST_AND_EXIT logic"
    assert "USER_SITE" in bootstrap_content, "Bootstrap should set USER_SITE environment variable"
    
    # Check that Python modules are present
    python_path = test_container.layer_path / "python"
    assert python_path.exists(), "Python path should exist"
    
    # Check for sitecustomize.py
    sitecustomize_path = python_path / "sitecustomize.py"
    assert sitecustomize_path.exists(), "sitecustomize.py should exist"
    
    sitecustomize_content = sitecustomize_path.read_text()
    assert "aws_xray_sdk" in sitecustomize_content, "sitecustomize.py should import aws_xray_sdk"
    assert "instrument" in sitecustomize_content, "sitecustomize.py should contain instrument function"
    
    # Check for aws-xray-sdk package
    aws_xray_path = python_path / "aws_xray_sdk"
    assert aws_xray_path.exists(), "aws_xray_sdk package should exist"
    
    # Check for wrapt package
    wrapt_path = python_path / "wrapt"
    assert wrapt_path.exists(), "wrapt package should exist"


def _find_project_root() -> Path:
    current_dir = Path(__file__).parent
    while not (current_dir / "pyproject.toml").exists():
        current_dir = current_dir.parent
    return current_dir
