import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def test_sitecustomize(request):
    import docker
    import time
    import zipfile
    import tempfile

    project_root = _find_project_root()
    layer_zip = project_root / "dist" / "layer.zip"
    assert (
        layer_zip.exists()
    ), f"Layer zip file does not exist: {layer_zip}, run make before running this test"

    client = docker.from_env()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

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
        if layer_bin_path.exists():
            # Run container with mounted layer_zip/bin to /opt/bin in RO mode
            logger.debug(
                f"Running container with image {image.id} and layer {layer_bin_path}"
            )
            container = client.containers.run(
                image.id,
                volumes={str(layer_bin_path): {"bind": "/opt/bin", "mode": "ro"}},
                detach=True,
                auto_remove=True,
                environment={
                    "TEST_AND_EXIT": "1",
                    "TEST_AND_EXIT_TIMEOUT": "2",
                    "AWS_LAMBDA_EXEC_WRAPPER": "/opt/bin/bootstrap",
                },
            )
            logger.debug(f"Container started: {container.id}")

            time.sleep(5)

            logs = container.logs().decode("utf-8")
            print(logs)

            assert "TEST_AND_EXIT: Command output:" in logs, f"TEST_AND_EXIT: Command output not found in logs: {logs}"

            # Clean up container
            logger.debug("Stopping container")
            container.stop()
            container.wait()
            logger.debug("Container stopped")

        # Clean up image
        def fin():
            logger.debug("Removing image")
            client.images.remove(image.id, force=True)
            logger.debug("Image removed")

        request.addfinalizer(fin)


def _find_project_root() -> Path:
    current_dir = Path(__file__).parent
    while not (current_dir / "pyproject.toml").exists():
        current_dir = current_dir.parent
    return current_dir
