import logging
import sys
import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests to output to stdout in debug mode."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Set specific logger for tests package to debug
    logger = logging.getLogger("tests")
    logger.setLevel(logging.DEBUG)
    
    # Ensure the logger propagates to the root logger
    logger.propagate = True