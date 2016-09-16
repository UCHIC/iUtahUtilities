"""

Tool for updating iUtah GAMUT data in HydroShare and CKAN repositories

"""

import datetime
import os
import re
import smtplib
import sys

__title__ = 'iUtahUtilities Update Tool'
WINDOWS_OS = 'nt' in os.name
DIR_SYMBOL = '\\' if WINDOWS_OS else '/'
PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(PROJECT_DIR))

import GAMUTRawData.CSVCreatorUpdate as CSV_Creator
from exceptions import IOError
from Utilities.HydroShareUtility import HydroShareUtility
from Utilities.CkanUtility import CkanUtility

EMAIL_SERVER = "mail.usu.edu"
EMAIL_FROM = "CSVgenerator@GAMUT.exe"
EMAIL_SUBJECT = "CSV Generator Report"
FORMAT_STRING = '%s  %s: %s'

curr_year = datetime.datetime.now().strftime('%Y')
file_path = '{root}{slash}GAMUT_CSV_Files{slash}'.format(root=PROJECT_DIR, slash=DIR_SYMBOL)
log_file = '{file_path}csvgenerator.log'.format(file_path=file_path)
dump_location = '{file_path}{year}{slash}'.format(file_path=file_path, year=curr_year, slash=DIR_SYMBOL)
RE_SITE_CODE = r'(^.*iUTAH_GAMUT_)(.*)(_rawdata_{year}\.csv$)'.format(year=curr_year)
RE_RESOURCE_FILTER = r"(?=.*raw.?data)(?=.*iUtah)(?=.*Gamut).+"


class Arguments:
    """
    Class for defining and parsing command line arguments
    """
    def __init__(self, args):
        self.VALID_HS_TARGETS = ['all', 'hydroshare', 'hs']
        self.VALID_CKAN_TARGETS = ['all', 'ckan']
        self.destination = 'none'
        self.verbose = False
        self.debug = False
        self.auth = {}
        for arg in args:
            if '--destination=' in arg:
                self.destination = str.lower(arg.split('--destination=')[1])
            elif '-d=' in arg:
                self.destination = str.lower(arg.split('-d=')[1])
            elif '--verbose' in arg:
                self.verbose = True
            elif '--username=' in arg:
                self.auth['username'] = arg.split('--username=')[1]
            elif '--password=' in arg:
                self.auth['password'] = arg.split('--password=')[1]
            elif '--client_id=' in arg:
                self.auth['client_id'] = arg.split('--client_id=')[1]
            elif '--client_secret=' in arg:
                self.auth['client_secret'] = arg.split('--client_secret=')[1]
            elif '--auth_file=' in arg:
                self.auth['auth_file'] = arg.split('--auth_file=')[1]
            elif '--debug' in arg:
                self.debug = True

    def validate(self):
        valid_args = True
        if self.destination not in self.VALID_HS_TARGETS and self.destination not in self.VALID_CKAN_TARGETS \
                and self.destination != 'none':
            valid_args = False
        if 'username' in self.auth and 'password' not in self.auth:
            valid_args = False
        if 'client_id' in self.auth and 'client_secret' not in self.auth:
            valid_args = False
        if 'auth_file' in self.auth and not os.path.exists(self.auth['auth_file']):
            valid_args = False
        return valid_args

    def print_usage_info(self):
        help_string = ("\nLoadCKAN Tool" +
                       "\n   -d=hs     --destination=hs       Update resource file on Hydroshare" +
                       "\n   -d=ckan   --destination=ckan     Update resource file on CKAN" +
                       "\n   -d=all    --destination=all      Update resource file on both servers" +
                       "\n   --auth_file=<path>               Absolute or relative path of credentials file" +
                       "\n   --debug                          Not currently used" +
                       "\n   --verbose                        Prints to stdout as well as to log file" +
                       "\n   --username=<username>            Username for Hydroshare account" +
                       "\n   --password=<password>            Password for given username" +
                       "\n   --client-id=<client id>          Client id given by HydroShare API" +
                       "\n   --client-secret=<secret>         Client secret given by HydroShare API")
        original_output = None
        if not sys.__stdout__ == sys.stdout:
            print(help_string)
            original_output = sys.stdout
            sys.stdout = sys.__stdout__
        print(help_string)
        print(sys.argv)
        if original_output is not None:
            sys.stdout = original_output


class Logger(object):
    """
    Overrides Python print function and maintains the program log file
    """

    def __init__(self, logfile, overwrite=False):
        self.terminal = sys.stdout
        if overwrite:
            mode = 'w'
        else:
            mode = 'a'
        self.log = open(logfile, mode=mode)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)


def send_email(issue_list, to, attach=None):
    print("Sending email with {} issues".format(len(issue_list)))
    message = ""
    for i in issue_list:
        message += '\n{}'.format(i)

    recipients = [to]  # must be a list
    file_content = ""

    try:
        fo = open(attach, "r")
        for f in fo.readline():
            file_content += "\n" + f
    except IOError as e:
        print('File Error: {}'.format(e))

    email_body = """
    From:  {sender}
    To: {recipients}
    Subject: GAMUT CSV Report

    CSV generater had the following issues when it was run at {start_time}:
    {message}

    log_file={log_file}:
    {file_content}
    """

    email_body = email_body.format(sender=EMAIL_FROM, recipients=recipients,
                                   start_time=datetime.datetime.now().strftime('%Y-%m-%d %H'),
                                   message=message, log_file=log_file, file_content=file_content)

    # Send the mail
    server = smtplib.SMTP(EMAIL_SERVER)
    server.sendmail(EMAIL_FROM, recipients, email_body)
    server.quit()


def getHydroShareCredentials(auth_info):
    username = None
    password = None
    client_id = None
    client_secret = None
    if 'username' in auth_info and 'password' in auth_info:
        username = auth_info['username']
        password = auth_info['password']
    if 'client_id' in auth_info and 'client_secret' in auth_info:
        client_id = auth_info['client_id']
        client_secret = auth_info['client_secret']
    if 'auth_file' in auth_info:
        auth_file = open(auth_info['auth_file'], 'r')
        username, password = auth_file.readline().split()
        client_id, client_secret = auth_file.readline().split()
    return {'client_id': client_id, 'client_secret': client_secret, 'username': username, 'password': password}


if __name__ == "__main__":
    user_args = Arguments(sys.argv)
    if not user_args.validate():
        user_args.print_usage_info()
        exit(0)
    if not os.path.exists(dump_location):
        os.makedirs(dump_location)
    if user_args.verbose:
        sys.stdout = Logger(log_file, overwrite=True)
    else:
        sys.stdout = open(log_file, 'w')

    issue_list = []
    # Fetch the raw GAMUT data and store them in CSV files locally
    try:
        issues = CSV_Creator.dataParser(dump_loc=dump_location, year=curr_year)
        issue_list.append(issues)
    except Exception as e:
        print('Exception encountered while retrieving datasets: {}'.format(e))
        issue_list.append(e)

    # Get names of all files, add to dictionary for processing`
    filename_list = []
    for item in os.listdir(dump_location):
        file_to_upload = dump_location + item
        result = re.match(RE_SITE_CODE, item, re.IGNORECASE)
        if result:
            filename_list.append({"path": file_to_upload, "name": item, "site": result.group(2)})

    # Start the upload process to Hydroshare
    if user_args.destination in user_args.VALID_HS_TARGETS:
        print("Preparing to upload files to HydroShare")
        hydroshare = HydroShareUtility()
        user_auth = getHydroShareCredentials(user_args.auth)
        if hydroshare.authenticate(**user_auth):
            paired_files, unpaired_files = hydroshare.pairFilesToResources(filename_list, RE_RESOURCE_FILTER)
            print('{}/{} resources found: {}'.format(len(paired_files), len(paired_files) + len(unpaired_files),
                                                     [item['file']['name'] for item in paired_files]))
            result = [] if user_args.debug else hydroshare.upload(paired_files)
            issue_list.extend(result)
            issue_list.extend(["No target resource found for {}".format(item['name']) for item in unpaired_files])

    # Perform upload to CKAN
    if user_args.destination in user_args.VALID_CKAN_TARGETS:
        print("Uploading files to CKAN")
        ckan_api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"
        ckan = CkanUtility(ckan_api_key, dump_location)
        result = ckan.upload(filename_list)
        issue_list.extend(result)

    # Notify on issues found
    if user_args.debug:
        for issue in issue_list:
            print issue
    elif len(issue_list) > 0:
        # send_email(issue_list, "stephanie.reeder@usu.edu", log_file)
        send_email(issue_list, "fryarludwig@gmail.com", log_file)
