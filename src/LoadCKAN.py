"""
Calling Format:
>python iutah_ckan_client.py update_resource 'value for api_key' *name of the dataset* 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv

Tried:
update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
update_resource 516ca1eb-f399-411f-9ba9-49310de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
"""

import datetime
import os
import re
import smtplib
import sys

import GAMUTRawData.CSVCreatorUpdate as CSV_Creator
from Utilities.HydroShareUtility import HydroShareUtility
from Utilities.CkanUtility import CkanUtility

EMAIL_SERVER = "mail.usu.edu"
EMAIL_FROM = "CSVgenerator@GAMUT.exe"
EMAIL_SUBJECT = "CSV Generator Report"
FORMAT_STRING = '%s  %s: %s'

NOW = datetime.datetime.now()
curr_year = NOW.strftime('%Y')

dump_location = "C:\\GAMUT_CSV_Files\\"
RE_SITE_CODE = r"(^.*iUTAH_GAMUT_)(.*)(_rawdata_" + curr_year + r"\.csv$)"
RE_GAMUT_RESOURCE_FILTER = r"(?:iUTAH|GAMUT)"

filename = 'csvgenerator.log'
filepath = dump_location + filename
# sys.stdout = open(filepath, 'w')
dump_location = "%s%s\\" % (dump_location, curr_year)


def send_email(issue_list, to, attach=None):
    print("Sending email with %s issues" % str(len(issue_list)))
    message = ""
    for i in issue_list:
        message = """%s
        %s""" % (message, str(i))

    recipients = [to]  # must be a list
    fo = open(attach, "r")
    filecontent = ""
    for f in fo.readline():
        filecontent = filecontent + "\n" + f
    # encodedcontent = base64.b64encode(filecontent)  # base64

    emailbody = """From:  {}
    To: {}
    Subject: GAMUT CSV Report

    """.format(EMAIL_FROM, recipients)
    emailbody += "CSV generater had the following issues when it was run at " + datetime.datetime.now().strftime(
        '%Y-%m-%d %H') + ":\n" + message
    emailbody += """

    filename={}:
    {}

    """.format(filename, filecontent.replace("\n", """
    """))

    print(emailbody)

    # Send the mail
    # server = smtplib.SMTP('localhost')
    server = smtplib.SMTP(EMAIL_SERVER)
    server.sendmail(EMAIL_FROM, recipients, emailbody)
    server.quit()


def run_tool(upload_to_ckan, upload_to_hydroshare):
    issue_list = []
    # Fetch the raw GAMUT data and store them in CSV files locally
    try:
        issues = CSV_Creator.dataParser(dump_loc=dump_location, year=curr_year)
        issue_list.append(issues)
    except Exception as e:
        issue_list.append(e)

    # Get names of all files, add to dictionary for processing
    filename_list = []
    for item in os.listdir(dump_location):
        file_to_upload = dump_location + item
        result = re.match(RE_SITE_CODE, item, re.IGNORECASE)
        filename_list.append({"path": file_to_upload, "name": item, "site": result.group(2)})

    # print filename_list

    if upload_to_ckan:
        print("Uploading files to CKAN")
        ckan_api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"  # "516ca1ebf399411f9ba949310de285f3"
        ckan = CkanUtility(ckan_api_key)
        result = ckan.upload(filename_list)
        if len(result) > 0:
            issue_list.append(result)
    if upload_to_hydroshare:
        print("Uploading files to HydroShare")

        auth_file = open("secret", 'r')
        username, password = auth_file.readline().split()
        client_id, client_secret = auth_file.readline().split()

        hydroshare = HydroShareUtility()
        if hydroshare.authenticate(username, password, client_id, client_secret):
            hydroshare.filterResourcesByRegex()
            result = hydroshare.upload(filename_list)
            if len(result) > 0:
                issue_list.append(result)

    if len(issue_list) > 0:
        # send_email(issue_list, "stephanie.reeder@usu.edu", filepath)
        send_email(issue_list, "fryarludwig@gmail.com", filepath)

    print("completed operations")
    for issue in issue_list:
        print("Issue: {}".format(issue))


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
