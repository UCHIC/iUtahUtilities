"""

Tool for updating iUtah GAMUT data in HydroShare and CKAN repositories

"""

import datetime
import os
import re
import smtplib
import sys
import xml.etree.ElementTree as ElementTree

__title__ = 'iUtahUtilities Update Tool'
WINDOWS_OS = 'nt' in os.name
DIR_SYMBOL = '\\' if WINDOWS_OS else '/'
PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(PROJECT_DIR))

from GAMUTRawData.CSVDataFileGenerator import *
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

# Raw Data strings and patterns
raw_dump_location = '{path}RawData{slash}{year}{slash}'.format(path=file_path, year=curr_year, slash=DIR_SYMBOL)
RE_RAW_DATA_SITE_CODE = r'(^.*iUTAH_GAMUT_)(?P<site>.*)(_rawdata_{year}\.csv$)'.format(year=curr_year)
RE_RAW_RESOURCES = r"(?=.*raw.?data)(?=.*iUtah)(?=.*Gamut).+"
RE_RAW_FILE = r'^.*(?P<name>(?P<required>iUTAH_GAMUT_)(?P<unused_1>.*)(' \
              r'_rawdata_)(?P<year>20[0-9]{2})(?P<duplicated>.*?)(?P<filetype>\.csv))$'

# Quality Control Level 1 strings and patterns
qc_dump_location = '{file_path}QualityControlled{slash}'.format(file_path=file_path, slash=DIR_SYMBOL)
RE_QC1_RESOURCES = r"(?=.*quality.?control.?level.?1.?)(?=.*iUtah)(?=.*Gamut).+"
RE_QC1_DATA_SITE_CODE = r'(^.*iUTAH_GAMUT_)(?P<site>.*)(_Quality_Control_Level_1_)(?P<var>.+)(\.csv$)'
RE_QC1_FILE = r'^.*(?P<name>(?P<required>iUTAH_GAMUT_)(?P<unused_1>.*)(_Quality_Control_Level_1_)(?P<var_code>.*)(' \
              r'?P<duplicated>(_[a-z0-9]{7})|((%20|\ )\([0-9]+\)))(?P<filetype>\.csv))$'


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
        if overwrite or not os.path.exists(logfile):
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


def uploadToHydroShare(user_auth, sites, resource_regex, file_regex, create_as_needed=False):
    """

    :param new_resource_name: For sites without resources, create a resource
    :type new_resource_name: str
    :param file_regex: Regular expression string used to break down the file name into useable parts
    :type file_regex: str
    :param user_auth: Authentication deta02ils
    :type user_auth: dict
    :param sites: Dictionary of sites with site files
    :type sites: dict of list of FileDetails
    :param resource_regex:
    :type resource_regex: str
    :return:
    :rtype:
    """
    hsResults = []
    hydroshare = HydroShareUtility()
    user_auth = getHydroShareCredentials(user_auth)
    if hydroshare.authenticate(**user_auth):
        print("Successfully authenticated. Getting resource_cache and checking for duplicated files")
        discovered_resources = hydroshare.filterOwnedResourcesByRegex(resource_regex)

        # Remove any duplicate files we can find
        print 'Checking for duplicate files in {} resources'.format(len(discovered_resources))
        for resource_id in discovered_resources:
            hydroshare.purgeDuplicateGamutFiles(resource_id, file_regex)

        # Check for matching resources for each site - we can't update a resource if we don't know what it is
        paired_sites, unpaired_sites = hydroshare.pairSitesToResources(sites.keys(), discovered_resources)

        # Create new resources if needed, and add the new resource to the site/resource pair list
        if create_as_needed:
            for site_code in unpaired_sites:
                valid_files = [f for f in sites[site_code] if not f.is_empty]
                if len(valid_files) == 0:
                    continue
                resource_details = getNewQC1ResourceInformation(site_code, valid_files)
                resource_id = hydroshare.createNewResource(resource_details)
                paired_sites.append({'resource_id': resource_id, 'site_code': site_code})
                unpaired_sites.remove(site_code)

        # Upload new, proper files - delete files that have been uploaded and are empty
        for pair in paired_sites:
            site_code = pair['site_code']
            hydroshare.removeResourceFiles([f for f in sites[site_code] if f.is_empty], pair['resource_id'])
            hydroshare.upload([f for f in sites[site_code] if not f.is_empty], pair['resource_id'])

        # Make sure our resources are public, this has potential to change if a resource has only one file
        hydroshare.setResourcesAsPublic(discovered_resources)

        # And we're done - let's report our results
        paired_site_codes = [item['site_code'] for item in paired_sites]
        print('{}/{} resource_cache found: {}'.format(len(paired_site_codes), len(sites.keys()), paired_site_codes))
        print 'The following sites have no valid files and/or no target resource: {}'.format(unpaired_sites)

        # Use this to delete any mistakenly created resource - but make sure the REGEX is correct
        if False:
            resources_to_delete = hydroshare.filterOwnedResourcesByRegex(RE_QC1_RESOURCES)
            for resource_id in resources_to_delete:
                hydroshare.deleteResource(resource_id, confirm=False)

    return hsResults


if __name__ == "__main__":
    user_args = Arguments(sys.argv)
    if not user_args.validate():
        user_args.print_usage_info()
        exit(0)
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    if not os.path.exists(raw_dump_location):
        os.makedirs(raw_dump_location)
    if not os.path.exists(qc_dump_location):
        os.makedirs(qc_dump_location)
    if user_args.verbose:
        sys.stdout = Logger(log_file, overwrite=True)
    else:
        sys.stdout = open(log_file, 'w')

    start_time = datetime.datetime.now()
    raw_files = {}
    qc_files = {}

    # Update the local Raw Data files
    raw_files = dataParser(raw_dump_location, 'Raw', curr_year)
    print 'Raw files updated - time taken: {}'.format(datetime.datetime.now() - start_time)

    # Update the local Quality Control Level 1 files
    stopwatch_timer = datetime.datetime.now()
    qc_files = dataParser(qc_dump_location, 'QC', curr_year)
    print 'QC Level 1 files updated - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)

    # Start the upload process to Hydroshare
    if user_args.destination in user_args.VALID_HS_TARGETS:
        print "\nRAW:"
        stopwatch_timer = datetime.datetime.now()
        uploadToHydroShare(user_args.auth, raw_files, RE_RAW_RESOURCES, RE_RAW_FILE)
        print 'Raw files uploaded - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)
        print "\n\nQC:"
        stopwatch_timer = datetime.datetime.now()
        uploadToHydroShare(user_args.auth, qc_files, RE_QC1_RESOURCES, RE_QC1_FILE, create_as_needed=True)
        print 'QC Level 1 files uploaded - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)

    # Perform upload to CKAN
    if user_args.destination in user_args.VALID_CKAN_TARGETS:
        stopwatch_timer = datetime.datetime.now()
        print("Uploading files to CKAN")
        ckan_api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"
        ckan = CkanUtility(ckan_api_key, raw_dump_location)
        result = ckan.upload(raw_files)
        for issue in result:
            print issue
        print 'Raw files uploaded to CKAN - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)

    # # Notify on issues found
    # if len(issue_list) > 0:
    #     for issue in issue_list:
    #         print issue
    #     # send_email(issue_list, "stephanie.reeder@usu.edu", log_file)
    #     if not user_args.debug:
    #         send_email(issue_list, "fryarludwig@gmail.com", log_file)

    print 'Program finished running - total time: {}'.format(datetime.datetime.now() - start_time)
