import CKANClient.iutah_ckan_client  as cc
import GAMUTRawData.CSVCreatorUpdate as cr
import datetime
import os
import sys

formatString = '%s  %s: %s'

this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)


issue_list=[]
NOW = datetime.datetime.now()
curr_year = NOW.strftime('%Y')
#curr_year="2014"
dump_location = "C:\\GAMUT_CSV_Files\\"

filename = 'csvgenerator.log'
filepath =  dump_location + filename
sys.stdout = open(filepath, 'w')
dump_location = "%s%s\\"%(dump_location,  curr_year)

import smtplib
def sendEmail(message, to, attach = None):
    SERVER = "mail.usu.edu"

    FROM = "CSVgenerator@GAMUT.exe"
    TO = [to] # must be a list

    SUBJECT = "CSV Generator Report"

    TEXT = "CSV generater had the following issues when it was run at "+ datetime.datetime.now().strftime('%Y-%m-%d %H') \
           +":\n" +message

    fo = open(attach, "r")
    filecontent = fo.read()
    #encodedcontent = base64.b64encode(filecontent)  # base64

    # Define the main headers.
    part1 = """From:  <%s>
    To: <%s>
    Subject: GAMUT CSV Report

    """ % (FROM, TO)

    # Define the attachment section
    part2 = """

    filename=%s:
    %s

    """ %( filename, filecontent.replace("\n", """
    """) )

    msg= part1 +  TEXT + part2
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

#update all of the files
try:
    issues = cr.dataParser(dump_loc = dump_location, year = curr_year)
    issues = "this is a test for my list of issues"
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

        #print formatString %(datetime.datetime.now(), "LoadCKAN",  "Replacing file %s on ckan repository"% f)
        #cc.update_resource(api_key, package_name, file_to_upload, replace_file_name, None)
    except Exception as e:
        print ("issue : %s, file: %s\n"% (e, f))
        issue_list.append(e)

if len(issue_list)>0:
    print("Sending email with %s issues"% str(len(issue_list)))
    m = ""
    for i in issue_list:
        m =  """%s
        %s"""%(m, str(i))
    sendEmail(m, "stephanie.reeder@usu.edu", filepath)

    #send email
