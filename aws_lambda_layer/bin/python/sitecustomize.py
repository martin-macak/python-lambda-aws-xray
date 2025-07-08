"""
AWS X-Ray Lambda Layer Auto-Instrumentation

This module automatically instruments Python code with AWS X-Ray tracing when
it's imported. It's placed in the sitecustomize.py file to be automatically
executed when the Python interpreter starts.

The instrumentation checks for required dependencies and versions before
applying AWS X-Ray patches to ensure compatibility.
"""

import logging
import os

logger = logging.getLogger("python-lambda-aws-xray")
# Configure logging to stdout
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
handler.stream = os.sys.stdout
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def setup():
    """
    Setup the AWS X-Ray instrumentation.
    """
    if os.environ.get("AWS_LAMBDA_AWS_XRAY_LOGGING_LEVEL", "INFO") == "DEBUG":
        logger.setLevel(logging.DEBUG)


def instrument():
    """
    Automatically instruments Python code with AWS X-Ray tracing.

    This function performs the following steps:
    1. Checks if botocore is available in the runtime
    2. Verifies botocore version meets minimum requirement (>=1.11.3)
    3. Applies AWS X-Ray patching to common AWS services and libraries

    The function gracefully handles missing dependencies by logging warnings
    and continuing without instrumentation rather than failing.
    """
    # Check if botocore is available in the Lambda runtime
    # botocore is provided by Lambda runtime but not included in the layer
    logger.debug("Instrumenting AWS X-Ray")

    try:
        import botocore
        logger.debug("botocore package is available")
    except ImportError:
        logger.warning(
            "botocore package is not available. Skipping AWS X-Ray instrumentation."
        )
        return

    # Verify botocore version meets AWS X-Ray SDK requirements
    # AWS X-Ray SDK for Python requires botocore >= 1.11.3
    from packaging import version

    if version.parse(botocore.__version__) < version.parse("1.11.3"):
        logger.warning(
            f"botocore version {botocore.__version__} is less than required 1.11.3. Skipping AWS X-Ray instrumentation."
        )
        return

    logger.debug("botocore version is >= 1.11.3")

    # Import and apply AWS X-Ray patching to common services
    # patch_all() instruments boto3, botocore, requests, and other supported libraries
    try:
        from aws_xray_sdk.core import patch_all

        # double_patch=True allows re-patching if called multiple times
        logger.debug("patching all")
        patch_all(double_patch=True)
        logger.debug("AWS X-Ray instrumentation successfully applied.")
    except ImportError:
        logger.warning(
            "aws_xray_sdk package is not available. Skipping AWS X-Ray instrumentation."
        )
        return


# Automatically instrument when the module is imported
# This happens when Python starts due to sitecustomize.py being automatically imported
setup()
instrument()
