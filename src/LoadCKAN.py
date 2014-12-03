import CKANClient.iutah_ckan_client  as cc
import GAMUTRawData.CSVCreatorUpdate as cr
import datetime
import os

import smtplib
def sendEmail(message, to):
    SERVER = "localhost"

    FROM = "sender@example.com"
    TO = [to] # must be a list

    SUBJECT = "Hello!"

    TEXT = "This message was sent with Python's smtplib." +message

    # Prepare actual message

    message = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    # Send the mail

    server = smtplib.SMTP(SERVER)
    server.sendmail(FROM, TO, message)
    server.quit()

'''
Calling Format:
>python iutah_ckan_client.py 'update_resource' 'value for api_key' 'name of the dataset' 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py 'update_resource' 'db567980cgt8906745678' 'my-original-dataset' 'c:\\odm_site_1_2014.csv' 'odm_site_1_2014.csv'
'''
issue_list=[]
NOW = datetime.datetime.now()
curr_year = NOW.strftime('%Y')
dump_location = "C:\\Users\\Stephanie\\Desktop\\csvsites\\"

#update all of the files
try:
    issues = cr.dataParser(dump_loc = dump_location)
    issue_list.append(issues)
except Exception as e:
    issue_list.append(e)


for f in os.listdir(dump_location):
    try:
        group= f.split("_")
        site_code = group[2]+"_"+group[3]+"_"+group[4]
        regex = "(?<=GAMUT_).*(?=_RawData)"

        api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"#"516ca1ebf399411f9ba949310de285f3"
        package_name = "iutah-gamut-network-raw-data-at-" + site_code.lower().replace('_', '-')
        file_to_upload = dump_location+ f #"iUTAH_GAMUT_"+site_code+"_RawData_"+curr_year+".csv"
        replace_file_name = f



        resource_info = None
        if False: #TODO if this is jan 1 of a new year
            params = {}
            params['CKAN_APIKEY'] = api_key
            params['FILENAME'] = os.path.basename(file_to_upload)

            params['NOW'] = NOW.isoformat()
            params['DIRECTORY'] = params['NOW'].replace(":", "").replace("-", "")
            resource_info = {
                "package_id": package_name,
                "revision_id": params['NOW'],
                "description": "Raw Data for Calendar year "+ curr_year,
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

        cc.update_resource(api_key, package_name, file_to_upload, replace_file_name, None)
    except Exception as e:
        issue_list.append(e)

if len(issue_list)>0:
    m = "CSV generater had the following issues when it was run at "+ datetime.datetime.now().strftime('%Y-%m-%d %H') +"\n"
    for i in issue_list:
        m = +  i + '\n'
    sendEmail(m, "stephanie.reeder@usu.edu")
    pass
    #send email
