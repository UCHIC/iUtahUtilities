import CKANClient.iutah_ckan_client  as cc
import GAMUTRawData.CSVCreatorUpdate as cr
import datetime
import os
import sys
import logging
import base64


this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)
from GAMUTRawData.logger import LoggerTool

tool = LoggerTool()
logger = tool.setupLogger(__name__, __name__+'.log', 'a', logging.DEBUG)

filename = 'csvgenerator.log'
sys.stdout = open(filename, 'w')




import smtplib
def sendEmail(message, to, attach = None):
    SERVER = "mail.usu.edu"

    FROM = "CSVgenerator@GAMUT.exe"
    TO = [to] # must be a list

    SUBJECT = "CSV Generator Errors"

    TEXT = "CSV generater had the following issues when it was run at "+ datetime.datetime.now().strftime('%Y-%m-%d %H') \
           +"\n\n\n\n" +message

    fo = open(attach, "rb")
    filecontent = fo.read()
    encodedcontent = base64.b64encode(filecontent)  # base64

    marker = "AUNIQUEMARKER"

    body ="""
    This is a test email to send an attachement.
    """
    # Define the main headers.
    part1 = """From:  <%s>
    To: <%s>
    Subject: Sending Attachement
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary=%s
    --%s
    """ % (FROM, TO, marker, marker)

    # Define the message action
    part2 = """Content-Type: text/plain
    Content-Transfer-Encoding:8bit

    %s
    --%s
    """ % (body,marker)

    # Define the attachment section
    part3 = """Content-Type: multipart/mixed; name=\"%s\"
    Content-Transfer-Encoding:base64
    Content-Disposition: attachment; filename=%s

    %s
    --%s--
    """ %(filename, filename, encodedcontent, marker)

    msg= TEXT+ part1 + part2 + part3
    # Send the mail
    #server = smtplib.SMTP('localhost')
    server = smtplib.SMTP(SERVER)
    server.sendmail(FROM, TO, msg)
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
#curr_year="2014"
dump_location = "C:\\GAMUT_CSV_Files\\%s\\" % curr_year


#update all of the files
try:
    #issues = cr.dataParser(dump_loc = dump_location, year = curr_year)
    issues = "this is a test"
    issue_list.append(issues)
except Exception as e:
    issue_list.append(e)



api_key = "516ca1eb-f399-411f-9ba9-49310de285f3"#"516ca1ebf399411f9ba949310de285f3"
res = cc.get_package_list(api_key)

for f in os.listdir(dump_location):
    try:
        package_name = ""
        group= f.split("_")
        site_code = group[2]+"_"+group[3]+"_"+group[4]
        #regex = "(?<=GAMUT_).*(?=_RawData)"
        for r in res:
            if site_code.lower().replace('_', '-') in r :
                package_name = r #res.pop(r)
                break

        #package_name = "iutah-gamut-network-raw-data-at-" + site_code.lower().replace('_', '-')
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
        logger.info("Replacing file %s on ckan repository"% f)
        print "Replacing file %s on ckan repository"% f
        #cc.update_resource(api_key, package_name, file_to_upload, replace_file_name, None)
    except Exception as e:
        logger.error("issue : %s, file: %s"% (e, f))
        issue_list.append(e)

if len(issue_list)>0:
    logger.info("Sending email with %s issues"% str(len(issue_list)))
    m = ""
    for i in issue_list:
        m =  m+ str(i) + '\n'
    sendEmail(m, "stephanie.reeder@usu.edu", filename)
    pass
    #send email
