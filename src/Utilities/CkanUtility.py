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

import CKANClient.iutah_ckan_client as cc


class CkanUtility():
    def __init__(self, api_key):
        self.NOW = datetime.datetime.now()
        self.curr_year = self.NOW.strftime('%Y')
        self.curr_date = self.NOW.strftime('%m %d')
        self.FORMAT_STRING = '%s  %s: %s'
        self.api_key = api_key

    def upload(self, file_list):
        res = cc.get_package_list(self.api_key)
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
                file_to_upload = self.dump_location + f
                replace_file_name = f
                if self.curr_date == "01 01":  # if this is jan 1 of a new year
                    params = {}
                    params['CKAN_APIKEY'] = self.ckan_api_key
                    params['FILENAME'] = os.path.basename(file_to_upload)

                    params['NOW'] = self.NOW.isoformat()
                    params['DIRECTORY'] = params['NOW'].replace(":", "").replace("-", "")
                    resource_info = {
                        "package_id": package_name,
                        "revision_id": params['NOW'],
                        "description": "Raw Data for Calendar year " + self.curr_year,
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
                print self.FORMAT_STRING % (datetime.datetime.now(), "LoadCKAN", "Replacing file %s on ckan repository" % f)
                print("Reached the update resource function call!")
                cc.update_resource(self.api_key, package_name, file_to_upload, replace_file_name, None)
            return []
        except Exception as e:
            print ("issue : %s, file: %s\n" % (e, f))
            return [e]


