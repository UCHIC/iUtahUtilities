import datetime
import os
import re
import smtplib
import sys
import GAMUTRawData.CSVCreatorUpdate as CSV_Creator
from exceptions import IOError
from Utilities.HydroShareUtility import HydroShareUtility
from Utilities.CkanUtility import CkanUtility

EMAIL_SERVER = "mail.usu.edu"
EMAIL_FROM = "CSVgenerator@GAMUT.exe"
EMAIL_SUBJECT = "CSV Generator Report"
FORMAT_STRING = '%s  %s: %s'

curr_year = datetime.datetime.now().strftime('%Y')

WINDOWS_OS = 'nt' in os.name
DIR_SYMBOL = '\\' if WINDOWS_OS else '/'
PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
AUTH_FILE_PATH = '{root}{slash}{auth}'.format(root=PROJECT_DIR, slash=DIR_SYMBOL, auth='secret')

file_path = '{root}{slash}GAMUT_CSV_Files{slash}'.format(root=PROJECT_DIR, slash=DIR_SYMBOL)
log_file = '{file_path}csvgenerator.log'.format(file_path=file_path)
dump_location = '{file_path}{year}{slash}'.format(file_path=file_path, year=curr_year, slash=DIR_SYMBOL)
RE_SITE_CODE = r'(^.*iUTAH_GAMUT_)(.*)(_rawdata_{year}\.csv$)'.format(year=curr_year)
RE_RESOURCE_FILTER = r"(?=.*raw.?data)(?=.*iUtah)(?=.*Gamut).+"

sys.stdout = open(log_file, 'w')


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


def getHydroShareCredentials(auth_file_name=AUTH_FILE_PATH):
    auth_file = open(auth_file_name, 'r')
    username, password = auth_file.readline().split()
    client_id, client_secret = auth_file.readline().split()
    return {'client_id': client_id, 'client_secret': client_secret, 'username': username, 'password': password}


def run_tool(upload_to_ckan, upload_to_hydroshare):
    issue_list = []
    # Fetch the raw GAMUT data and store them in CSV files locally
    try:
        if not os.path.exists(dump_location):
            os.makedirs(dump_location)
        issues = CSV_Creator.dataParser(dump_loc=dump_location, year=curr_year)
        issue_list.append(issues)
    except Exception as e:
        issue_list.append(e)

    # Get names of all files, add to dictionary for processing`
    filename_list = []
    for item in os.listdir(dump_location):
        file_to_upload = dump_location + item
        result = re.match(RE_SITE_CODE, item, re.IGNORECASE)
        if result:
            filename_list.append({"path": file_to_upload, "name": item, "site": result.group(2)})

    if upload_to_ckan:
        print("Uploading files to CKAN")
        ckan_api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"  # "516ca1ebf399411f9ba949310de285f3"
        ckan = CkanUtility(ckan_api_key, dump_location)
        result = ckan.upload(filename_list)
        issue_list.extend(result)
    if upload_to_hydroshare:
        print("Preparing to upload files to HydroShare")
        hydroshare = HydroShareUtility()
        user_auth = getHydroShareCredentials()
        if hydroshare.authenticate(**user_auth):
            paired_files, unpaired_files = hydroshare.pairFilesToResources(filename_list, RE_RESOURCE_FILTER)
            print('Target resource found for {}'.format([item['file']['name'] for item in paired_files]))
            result = hydroshare.upload(paired_files)
            issue_list.extend(result)
            issue_list.extend(["No target resource found for {}".format(item['name']) for item in unpaired_files])
            print([item['name'] for item in unpaired_files])

    if len(issue_list) > 0:
        # send_email(issue_list, "stephanie.reeder@usu.edu", log_file)
        send_email(issue_list, "fryarludwig@gmail.com", log_file)


def print_usage_info():
    help_string = ("\nLoadCKAN Tool" +
                   "\n   -d=hs     --destination=hs       Update resource file on Hydroshare" +
                   "\n   -d=ckan   --destination=ckan     Update resource file on CKAN" +
                   "\n   -d=all    --destination=all      Update resource file on both servers")
    if not sys.__stdout__ == sys.stdout:
        print(help_string)
        sys.stdout = sys.__stdout__
    print(help_string)
    print(sys.argv)
    exit(0)


if __name__ == "__main__":
    upload_to_ckan = False
    upload_to_hydroshare = False
    if len(sys.argv) == 2:
        user_arg = ['', 'None']
        if '--destination=' in sys.argv[1]:
            user_arg = sys.argv[1].split('--destination=')
        elif '-d=' in sys.argv[1]:
            user_arg = sys.argv[1].split('-d=')

        if user_arg[1] == "all" or user_arg[1] == "ckan":
            upload_to_ckan = True
        if user_arg[1] == "all" or user_arg[1] == "hs":
            upload_to_hydroshare = True
    if upload_to_ckan or upload_to_hydroshare:
        run_tool(upload_to_ckan, upload_to_hydroshare)
    else:
        print_usage_info()
