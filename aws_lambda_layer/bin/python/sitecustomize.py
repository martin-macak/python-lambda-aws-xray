import logging

logger = logging.getLogger("python-lambda-aws-xray")


def instrument():
    # Check if botocore is available
    try:
        import botocore
    except ImportError:
        logger.warning("botocore package is not available. Skipping AWS X-Ray instrumentation.")
        return
    
    # Check botocore version
    from packaging import version
    if version.parse(botocore.__version__) < version.parse("1.11.3"):
        logger.warning(f"botocore version {botocore.__version__} is less than required 1.11.3. Skipping AWS X-Ray instrumentation.")
        return
    
    # Import and apply AWS X-Ray patching
    try:
        from aws_xray_sdk.core import patch_all
        patch_all(double_patch=True)
    except ImportError:
        logger.warning("aws_xray_sdk package is not available. Skipping AWS X-Ray instrumentation.")
        return


instrument()
