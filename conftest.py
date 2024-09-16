import datetime
import os, sys
import shutil
import subprocess
import time
from multiprocessing import Process, Lock, Pool
import keyboard
import pyautogui
import pytest
import numpy as np
from parse import parse
from selenium import webdriver
from pathlib import Path
import json
import cv2
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


from Test_Resources.Utility.PropertiesUtility import ReadConfig

# import pytest_html_reporter
global driver
from selenium.webdriver.chrome.options import Options
from Test_Resources.Utility import Globals
from Test_Resources.Utility.Generic_Utils import Util as Utility
from reportportal_client import RPLogger, RPLogHandler
import logging
import pickle

import glob


# import pyttsx3


@pytest.fixture(scope="session")
def rp_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.setLoggerClass(RPLogger)
    return logger


@pytest.fixture(autouse=True, scope="session")
def driver(request):
    # print(request.config.option.browser)
    try:
        num_nodes = request.config.workerinput['workercount']
    except Exception as E:
        print("Not a parallel execution")
        num_nodes = 1

    Globals.environment = ReadConfig.getProperty('executionType')
    Globals.browserType = ReadConfig.getProperty('browser')
    print(Globals.browserType)

    if Globals.environment == "local":

        if Globals.browserType.upper() == "CHROME_HEADLESS":
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920x1080")
            driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)


        elif Globals.browserType.upper() == "CHROME":
            options = Options()
            options.page_load_strategy = 'normal'
            options.browser_version = '128'
            driver = webdriver.Chrome(options=options)

        elif Globals.browserType.upper() =="MSEDGE":
            driver = webdriver.Edge()


        elif Globals.browserType.upper() == "HEALING":
            options = webdriver.ChromeOptions()
            driver = webdriver.Remote('http://localhost:8085', options=options)




    elif Globals.environment == "remote":
        if Globals.browserType.upper() == "CHROME_GRID":
            remotehuburl = ReadConfig.getProperty("remotehuburl")
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument("--remote-allow-origins=*")
            chrome_options.add_argument("-avoidProxy")
            # chrome_options.set_capability("browserVersion", "95")
            # num_nodes = 3

            # if os.environ["Node_On"] == 'False':
            remotehuburl = ReadConfig.getProperty("remotehuburl")

            Utility.run_powershell_script(Globals.ps_script_path, num_nodes, remotehuburl)
            # os.environ["Node_On"] == 'True'

            driver = webdriver.Remote(
                command_executor=remotehuburl,
                options=chrome_options
            )

        elif Globals.browserType.upper() == "FIREFOX_GRID":
            remotehuburl = ReadConfig.getProperty("remotehuburl")
            chrome_options = webdriver.FirefoxOptions()
            driver = webdriver.Remote(
                command_executor=remotehuburl,
                options=chrome_options

            )

    elif Globals.environment == "cloud":

        if Globals.browserType.upper() == "CHROME_BROWSERSTACK":
            options = Options()
            options.accept_insecure_certs = True

            BS_ACCOUNT = Globals.bs_account
            BS_KEY = Globals.bs_key

            buildName = Globals.archiveReportFolder
            bstack_options = {
                "os": "Windows",
                "osVersion": "10",
                "browserVersion": "latest",
                "browserName": "Chrome",
            }
            options.set_capability("name", "Web Test")
            options.set_capability("projectName", "Alpha Automation")
            options.set_capability("sessionName", buildName)

            options.set_capability('bstack:options', bstack_options)

            driver = webdriver.Remote(command_executor=f'https://{BS_ACCOUNT}:{BS_KEY}@hub.browserstack.com/wd/hub',
                                      options=options)

            Globals.driver = driver
            Globals.browserStack = True




        elif Globals.browserType.upper() == "FIREFOX_BROWSERSTACK":
            options = Options()
            options.accept_insecure_certs = True

            BS_ACCOUNT = Globals.bs_account
            BS_KEY = Globals.bs_key

            buildName = Globals.archiveReportFolder
            bstack_options = {
                "os": "Windows",
                "osVersion": "10",
                "browserVersion": "latest",
                "browserName": "Firefox",
            }
            options.set_capability("name", "Web Test")
            options.set_capability("projectName", "Alpha Automation")
            options.set_capability("sessionName", buildName)

            options.set_capability('bstack:options', bstack_options)

            driver = webdriver.Remote(command_executor=f'https://{BS_ACCOUNT}:{BS_KEY}@hub.browserstack.com/wd/hub',
                                      options=options)

            Globals.driver = driver
            Globals.browserStack = True

    Globals.driver = driver
    yield driver
    if driver is not None:
        driver.quit()


def pytest_sessionstart(session):
    session.config.inicfg["render_collapsed"] = True
    global p, folder_path, screenshot_path
    print("STARTING SESSION")
    temp_path = "Test_Reports/default"
    screenshots = "Test_Reports/default/screenshots"
    delete_files_in_directory(temp_path)
    delete_files_in_directory("allure-results")
    delete_files_in_directory(screenshots)

    print("======FRAMEWORK==== Report Folder : " + Globals.archiveReportFolder)
    Globals.video_recording = ReadConfig.getProperty('executionVideo')
    if Globals.video_recording == "Yes":
        folder_path = "Test_Reports/default"
        p = Process(target=capturescreen, args=[folder_path])
        p.start()
        time.sleep(3)
        print("Process started")


def pytest_bdd_before_scenario(request, feature, scenario):
    print("Executing scenario")
    print(scenario.name)
    Globals.deviceType = request.config.option.device
    Globals.bs_account = ReadConfig.getProperty('browserstack_account')
    Globals.bs_key = ReadConfig.getProperty('browserstack_key')


def pytest_bdd_before_step(request, feature, scenario, step, step_func):
    Globals.stepCounter = Globals.stepCounter + 1
    screenshot_name = str(step.name).replace(" ", "_")
    scenario_name = str(scenario.name).replace(" ", "_")
    step_screenshot = scenario_name + "_" + screenshot_name
    print("****** STEP STARTING " + step_screenshot)
    logger = logging.getLogger(__name__)
    logger.info(f"STARTING STEP: {step.keyword} {step.name}")

    feature_name = feature.name
    scenario_name = scenario.name
    step_name = Globals.step_name.append(step.name)
    Globals.feature_name = feature_name
    Globals.scenario_name = scenario_name


def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
    screenshot_name = str(step.name).replace(" ", "_").replace('"', '')
    scenario_name = str(scenario.name).replace(" ", "_").replace('"', '')
    step_screenshot = "1_" + scenario_name + "_" + screenshot_name
    print("****** STEP COMPLETE " + step_screenshot)
    screenshot_file_path = Utility.capturescreenshot(step_screenshot)

    logger = logging.getLogger(__name__)
    # Utility.reportPortal_takeScreenshot(screenshot_file_path,step.name)
    logger.info(f"STEP COMPLETED: {step.keyword} {step.name}")

# def pytest_bdd_after_step(request, feature, scenario, step, step_func, step_func_args):
#     screenshot_name = str(step.name).replace(" ", "_")
#     scenario_name=str(scenario.name).replace(" ","_")
#     step_screenshot="1_"+scenario_name+"_"+screenshot_name
#     print("****** STEP COMPLETE "+step_screenshot)
#     screenshotcaptured=Utility.capturescreenshot(step_screenshot)
#     screenshots = "Test_Reports/default/screenshots"
#     request.node.screenshot = screenshots
#     request.node.screenshot_html = f'<img src="{screenshots}" alt="screenshot" width="800px">'

def pytest_sessionfinish(session):
    # print("This would be at the end of the Execution")
    print("[FRAMEWORK][SETUP]----------SESSION COMPLETED")
    os.makedirs(Globals.archiveReportFolder, exist_ok=True)
    source_directory = "Test_Reports/default"
    destination_directory = Globals.archiveReportFolder
    copy_files(source_directory, destination_directory)

    if Globals.video_recording == "Yes":
        keyboard.press("q")
        p.terminate()
        p.join()
        print("Process stopped")
        keyboard.press("backspace")

    try:
        driver = Globals.driver  # @updated from Utility to Globals
        if driver is not None:
            driver.quit()
    except Exception as E:
        # print(E)
        print("")

    report_folder = Globals.archiveReportFolder
    allurereportfolder = f"{report_folder}/Allure_Reports_" + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    Globals.allureReportFolder = allurereportfolder
    os.makedirs(allurereportfolder, exist_ok=True)
    copy_files("allure-results", allurereportfolder)

    src_dir = "Test_Reports/default"
    dst_dir = "Test_Reports/default/screenshots"
    for pngfile in glob.iglob(os.path.join(src_dir, "*.png")):
        shutil.copy(pngfile, dst_dir)
        os.remove(pngfile)


def pytest_html_report_title(report):
    report.title = "Enterra Automation Report"


# def pytest_html_results_table_header(cells):
#     cells.insert(2, "<th>Description</th>")
#
# def pytest_html_results_table_row(report, cells):
#     # Concatenate feature, scenario, and step names
#     description = f'<b>FEATURE:</b> {Globals.feature_name}<br><br><b>SCENARIO:</b> {Globals.scenario_name}<br><br><b>STEPS:</b>'
#
#     # Iterate through the step names and add them under the "STEPS:" section
#     for step in Globals.step_name:
#         description += f'<br>{step}'
#
#     cells.insert(2, '<td>' + description + '</td>')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    now = datetime.datetime.now()
    outcome = yield
    pytest_html = item.config.pluginmanager.getplugin('html')
    report = outcome.get_result()

    extra = getattr(report, 'extra', [])
    if report.when == 'setup':
        print("*** Starting Test Report")

    if report.when == 'call':
        # report.description = str(item.function.__doc__)
        screenshotFullPath = Globals.rootfolder + "/" + Globals.screenshot_path
        defaultFolderScreenshot = ""
        print(defaultFolderScreenshot)
        # html = '<p><a href="." target="_blank" align="right" style="width:304px;height:228px;" >Test Results</a></p>'

        description = f'<b>FEATURE:</b> {Globals.feature_name}<br><br><b>SCENARIO:</b> {Globals.scenario_name}<br><br><b>STEPS:</b>'
        for step in Globals.step_name:
            description += f'<br>{step}'

        html = f'<p>{description}<br><br><a href="." target="_blank" align="right" style="width:304px;height:228px;">Test Results</a></p>'
        extra.append(pytest_html.extras.html(html))
        xfail = hasattr(report, 'wasxfail')
        # if (report.skipped and xfail) or (report.failed and not xfail):
        # file_name = report.nodeid.replace("::", "_") + ".png"
        file_name = "screenshot" + now.strftime("%S%H%d%m%Y")
        Utility.capturescreenshot(file_name)
        try:
            import base64
            # Open the PNG image file in binary mode
            pathToConvertImage = Globals.rootfolder + "/" + Globals.screenshot_path + "/" + file_name + ".png"
            with open(pathToConvertImage, 'rb') as image_file:
                # Read the image file
                image_data = image_file.read()
            # Encode the image data in base64
            base64_encoded = base64.b64encode(image_data).decode('utf-8')

            # ******
            image_data = base64_encoded
            html_code = f'''


             <div style="max-width: 100%;overflow-x: auto; margin-bottom: 20px;">
            <!-- Your screenshot here with a maximum width -->
             <img src="data:image/png;base64,{image_data}" alt="Failed Screenshot" onclick="showOverlay(this)" style="width:500px;height:350px;" align="left">
             <br></br>
            </div>



            <script>
                ''' + '''function showOverlay(img) {
                    var overlay = document.querySelector('.overlay');
                    var overlayImage = document.querySelector('#overlay-image');

                    // Set the source of the overlay image
                    overlayImage.src = img.src;

                    // Display the overlay
                    overlay.style.display = 'block';
                }

                // Function to close the overlay
                function closeOverlay() {
                    var overlay = document.querySelector('.overlay');

                    // Hide the overlay
                    overlay.style.display = 'none';
                }


            </script>
            '''
            extra.append(pytest_html.extras.html(html_code))
            # ******
        except:
            screenshotLocal = Globals.rootfolder + "/" + Globals.screenshot_path + "/" + file_name + ".png"
            html = '<div><img src="%s" alt="screenshot" style="width:304px;height:228px;" ' \
                   'onclick="window.open(this.src)" align="right"/></div>' % screenshotLocal
            extra.append(pytest_html.extras.html(html))
        report.extra = extra

        if Globals.browserStack:
            browser = Globals.driver
            if report.passed:
                # For marking test as passed
                browser.execute_script(
                    'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"passed", "reason": "Test Passed Check Report"}}')
            elif report.failed:
                # For marking test as failed
                browser.execute_script(
                    'browserstack_executor: {"action": "setSessionStatus", "arguments": {"status":"failed","reason": "Test failed Check Report"}}')

    if report.when == "teardown":
        print("Reporting Complete for Test")


def capturescreen(resultfolder):
    global out
    SCREEN_SIZE = pyautogui.size()
    # define the codec
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    # fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    # create the video write object
    # out = cv2.VideoWriter(resultfolder + "Execution_recording.avi", fourcc, 20.0, (SCREEN_SIZE))

    # Create a VideoWriter object
    # output_file_path = os.path.join(resultfolder, "Test_Execution_recording.mp4")
    output_file_path = os.path.join(resultfolder, "Test_Execution_recording.avi")
    out = cv2.VideoWriter(output_file_path, fourcc, 20.0, (SCREEN_SIZE))

    while True:

        # make a screenshot
        img = pyautogui.screenshot()
        # convert these pixels to a proper numpy array to work with OpenCV
        frame = np.array(img)
        # convert colors from BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # write the frame
        out.write(frame)
        # show the frame
        # cv2.imshow("screenshot", frame)
        # if the user clicks 'esc', it exits
        if keyboard.is_pressed("q"):
            print("video break")
            break

    # make sure everything is closed when exited
    cv2.destroyAllWindows()
    out.release()


@pytest.fixture(scope="function")
def feature_name(request):
    # Extract feature name from the test name
    feature_name = request.node.name
    yield feature_name


@pytest.fixture
def context_data():
    context_data = {}
    return context_data


#
# @pytest.fixture
# def get_json_data(context_data):
#     def data_ret(testid, datafile):
#         dataFile = datafile
#         fileDirectory = 'Test_Data'
#         BASE_DIR = Path(__file__).resolve().parent
#         DATA_FILE = BASE_DIR.joinpath(fileDirectory).joinpath(dataFile)
#         file = open(DATA_FILE)
#         data = json.load(file)
#         for k in data.keys():
#             if k == testid:
#                 context_data.update(data[k])
#                 return data[k]
#
#     return data_ret


def pytest_runtestloop(session):
    source_directory = "Test_Reports/default"
    destination_directory = Globals.archiveReportFolder
    copy_files(source_directory, destination_directory)
    print("FINALE after all workers are completed")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # if sys.platform.startswith('win'):
    #     Globals.video_recording = 'Yes'
    # else:
    #     Globals.video_recording = 'No'
    # set custom options only if none are provided from command line
    if not config.option.htmlpath:
        now = datetime.datetime.now()
        Globals.stepCounter = 0
        archiveReportFolder = "Test_Reports/Test_Executions/TestReport" + datetime.datetime.now().strftime(
            '%Y%m%d_%H%M%S')
        Globals.archiveReportFolder = archiveReportFolder
        report = f"Test_Reports/default/AutomationReport.html"
        os.makedirs("Test_Reports/default", exist_ok=True)
        Globals.screenshot_path = "Test_Reports/default"
        # adjust plugin options
        config.option.htmlpath = report
        config.option.self_contained_html = True
        # config.option.css = [str(Path(context.configFolder_path+"/report.css"))]
        config.option.log = "Demo.log"


def pytest_bdd_step_error(request, feature, scenario, step, step_func, step_func_args, exception):
    # Save data using pickle as needed
    pickle_data = {
        "feature": feature.name,
        "scenario": scenario.name,
        "step": step.name,
        "exception": str(exception),
    }

    with open("report.pickle", "ab") as pickle_file:
        pickle.dump(pickle_data, pickle_file)


def delete_files_in_directory(directory_path):
    try:
        files = os.listdir(directory_path)
        for file in files:
            file_path = os.path.join(directory_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("All files deleted successfully.")
    except OSError:
        print("Error occurred while deleting files.")


def pytest_addoption(parser):
    parser.addoption("--browser", action="store", default="CHROME")
    parser.addoption("--execution", action="store", default="LOCAL")
    parser.addoption("--device", action="store", default="IOS")


def copy_files(source_dir, destination_dir):
    # Check if the source directory exists
    if not os.path.exists(source_dir):
        # print(f"Source directory '{source_dir}' does not exist.")
        return

    # Create the destination directory if it doesn't exist
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Get a list of all files in the source directory
    files = os.listdir(source_dir)

    # Iterate over the files and copy them to the destination directory
    for file in files:
        source_path = os.path.join(source_dir, file)
        destination_path = os.path.join(destination_dir, file)

        # Check if the file is a regular file (not a directory)
        if os.path.isfile(source_path):
            shutil.copy2(source_path, destination_path)
            # print(f"Copied '{file}' to '{destination_dir}'")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # terminalreporter is the reporter object for terminal output
    # exitstatus is the exit code of the test run
    # config is the pytest configuration object

    # You can perform actions or print messages here
    passed = terminalreporter.stats.get('passed', 0)
    failed = terminalreporter.stats.get('failed', 0)
    skipped = terminalreporter.stats.get('skipped', 0)

    # Print a summary message
    summary = f"Test run summary: Passed={passed}, Failed={failed}, Skipped={skipped}"
    terminalreporter.write_line(summary, bold=True, yellow=True)


def pytest_bdd_apply_tag(tag, function):
    if tag == 'todo':
        marker = pytest.mark.skip(reason="Not implemented yet")
        marker(function)
        return True
    if tag == "bug":
        marker = pytest.mark.issue(issue_id="111111", reason="data issue", issue_type="PB")
        marker(function)
        return True

    else:
        # Fall back to the default behavior of pytest-bdd
        return None

# @pytest.fixture(scope='session', autouse=True)
# def open_allure_report():
#     # This code will run after all tests have completed
#     yield
#
#     try:
#         sp = subprocess.run(["allure", "serve", "C:/PyTest_BDD_Framework/allure-results"],shell=True)
#         time.sleep(5)
#         sp.terminate()
#
#     except FileNotFoundError:
#         print("Allure command not found. Make sure 'allure' is in your PATH.")


