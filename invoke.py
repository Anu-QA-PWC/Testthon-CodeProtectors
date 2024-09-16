import os
import subprocess
import sys
import time
import pytest
from Test_Resources.Utility import Globals
from Test_Resources.Utility.PropertiesUtility import ReadConfig
import subprocess
import logging
import os

"""
Execution of all tests:
pytest

specific test:
pytest Tests\\step_definitions\\test_salesforce.py

report generation:
pytest --html=report.html  --self-contained-html 

parallel execution:
pytest -n 2 --> (2 worker processes created)

Markers:
pytest -m smoke -n 4
pytest -m smoke -n 4  --html=report.html  --self-contained-html 

Keywords:
pytest -k "TEST_1"
pytest -k "MyClass and not method"
pytest -k "TEST_1" --html=report.html  --self-contained-html

"""

args = [
    "Tests",
    "-m createscenario",
    # "-n  2",
    "--capture=tee-sys",
    "--alluredir=allure-results",
    "--reportportal",
    "--disable-pytest-warnings",
]

if __name__ == "__main__":

    # os.environ["Node_On"] == 'False'
    pytest.main(args)
    # stop nodes from docker
    if ReadConfig.getProperty('browser') == "CHROME_GRID":

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        try:
            image_name = "selenium/node-chrome:4.12.1-20230904"
            # image_name = "selenium/node-chrome:latest"

            command = f'for /f %c in (\'docker ps -q --filter "ancestor={image_name}"\') do docker stop %c'

            # Run the command in a shell
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for the process to complete and capture the output
            stdout, stderr = process.communicate()

            # Check the result
            if process.returncode == 0:
                logger.info("Command executed successfully")
            else:
                logger.error("Error: %s", stderr.decode('utf-8'))

        except Exception as e:
            logger.error("An error occurred: %s", str(e))

    try:
        allure_process = subprocess.Popen(["allure", "serve", Globals.allureReportFolder], shell=True)
        os.popen('allure generate --single-file allure-results --clean')
        time.sleep(5)
        allure_process.terminate()

    except FileNotFoundError:
        print("Allure command not found. Make sure 'allure' is in your PATH.")









