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
import smtplib
import sys
import re

import CKANClient.iutah_ckan_client as cc
import GAMUTRawData.CSVCreatorUpdate as cr

from hs_restclient import HydroShare, HydroShareAuthBasic, HydroShareAuthOAuth2

auth_file = open("secret", 'r')
username, password = auth_file.readline().split()
client_id, client_secret = auth_file.readline().split()

EMAIL_SERVER = "mail.usu.edu"
EMAIL_FROM = "CSVgenerator@GAMUT.exe"
EMAIL_SUBJECT = "CSV Generator Report"
FORMAT_STRING = '%s  %s: %s'

this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))
sys.path.insert(0, directory)

NOW = datetime.datetime.now()
curr_year = NOW.strftime('%Y')
curr_date = NOW.strftime('%m %d')
dump_location = "C:\\GAMUT_CSV_Files\\"
RESOURCE_TITLE = r"Test_Resource_iUTAH[\W_ -]*GAMUT"

filename = 'csvgenerator.log'
filepath = dump_location + filename
sys.stdout = open(filepath, 'w')
dump_location = "%s%s\\" % (dump_location, curr_year)

ckan_api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"  # "516ca1ebf399411f9ba949310de285f3"


def sendEmail(message, to, attach=None):
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


def ckan_upload(file_list):
    res = cc.get_package_list(ckan_api_key)
    try:
        for curr_file in file_list:
            f = curr_file['path']
            package_name = ""
            group = f.split("_")
            site_code = group[2] + "_" + group[3] + "_" + group[4]
            for r in res:
                if site_code.lower().replace('_', '-') in r:
                    package_name = r
                    break
            file_to_upload = dump_location + f
            replace_file_name = f
            if curr_date == "01 01":  # if this is jan 1 of a new year
                params = {}
                params['CKAN_APIKEY'] = ckan_api_key
                params['FILENAME'] = os.path.basename(file_to_upload)

                params['NOW'] = NOW.isoformat()
                params['DIRECTORY'] = params['NOW'].replace(":", "").replace("-", "")
                resource_info = {
                    "package_id": package_name,
                    "revision_id": params['NOW'],
                    "description": "Raw Data for Calendar year " + curr_year,
                    "format": "CSV",
                    # "hash": None,
                    "name": params['FILENAME'],
                    # "resource_type": None,
                    "mimetype": "application/text",
                    "mimetype_inner": "text/csv",
                    # "webstore_url": None,
                    # "cache_url": None,
                    # "size": None,
                    "created": params['NOW'],
                    "last_modified": params['NOW'],
                    # "cache_last_updated": None,
                    # "webstore_last_updated": None,
                }
            print FORMAT_STRING % (datetime.datetime.now(), "LoadCKAN", "Replacing file %s on ckan repository" % f)
            print("Reached the update resource function call!")
            cc.update_resource(ckan_api_key, package_name, file_to_upload, replace_file_name, None)
        return []
    except Exception as e:
        print ("issue : %s, file: %s\n" % (e, f))
        return [e]


def hydroshare_upload(file_list, retry_on_failure=True):
    """ Connect as user and upload the files to HydroShare

    :param file_list: List of dictionaries in format [ {"name": "file_name", "path": "file_path" }, {...} ]
    :param retry_on_failure: If an exception occurs in this function, this function will call itself once more

    :return: An error string on multiple failures, and nothing on success
    """
    try:
        auth = HydroShareAuthOAuth2(client_id, client_secret, username=username, password=password)
        hs = HydroShare(auth=auth)
        user_info = hs.getUserInfo()
        print("Successfully authenticated with HydroShare")
        resource_list = hs.getResourceList(owner=user_info['username'])
        for resource in resource_list:
            if re.match(RESOURCE_TITLE, resource['resource_title'], re.IGNORECASE):
                remote_files = hs.getResourceFileList(resource['resource_id'])
                remote_file_names = [os.path.basename(files['url']) for files in remote_files]
                for local_file in file_list:
                    already_exists = [s for s in remote_file_names if local_file['name'] in s]
                    if len(already_exists) > 0:
                        hs.deleteResourceFile(resource['resource_id'], local_file['name'])
                    hs.addResourceFile(resource['resource_id'], local_file['path'])
                    print("{} uploaded to resource {}".format(local_file['path'], resource['resource_title']))
    except Exception as e:
        if retry_on_failure:
            return hydroshare_upload(file_list, retry_on_failure=False)
        else:
            return "Upload retry failed - could not complete upload to HydroShare due to exception: {}".format(e)
    return []


def run_tool(upload_to_ckan, upload_to_hydroshare):
    issue_list = []
    # try:
    #     issues = cr.dataParser(dump_loc=dump_location, year=curr_year)
    #     issue_list.append(issues)
    # except Exception as e:
    #     issue_list.append(e)

    filename_list = []
    for item in os.listdir(dump_location):
        file_to_upload = dump_location + item
        filename_list.append({"path": file_to_upload, "name": item})

    if upload_to_ckan:
        print("Uploading files to CKAN")
        result = ckan_upload(filename_list)
        if len(result) > 0:
            issue_list.append(result)
    if upload_to_hydroshare:
        print("Uploading files to HydroShare")
        result = hydroshare_upload(filename_list)
        if len(result) > 0:
            issue_list.append(result)

    if len(issue_list) > 0:
        print("Sending email with %s issues" % str(len(issue_list)))
        m = ""
        for i in issue_list:
            m = """%s
            %s""" % (m, str(i))
        sendEmail(m, "stephanie.reeder@usu.edu", filepath)
        # sendEmail(m, "fryarludwig@gmail.com", filepath)
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
