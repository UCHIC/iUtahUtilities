"""
Calling Format:
>python iutah_ckan_client.py update_resource 'value for api_key' *name of the dataset* 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
"""

import datetime

import CKANClient.iutah_ckan_client as cc


class CkanUtility:
    def __init__(self, api_key, dump_location):
        self.NOW = datetime.datetime.now()
        self.FORMAT_STRING = '%s  %s: %s'
        self.api_key = api_key
        self.dump_location = dump_location

    def upload(self, file_list):
        res = cc.get_package_list(self.api_key)
        try:
            for curr_file in file_list:
                package_name = ""
                site_code = curr_file['site']
                for r in res:
                    if site_code.lower().replace('_', '-') in r:
                        package_name = r
                        break

                if self.NOW.strftime('%m %d') == "01 01":  # if this is jan 1 of a new year
                    params = {}
                    params['CKAN_APIKEY'] = self.ckan_api_key
                    params['FILENAME'] = curr_file['name']
                    params['NOW'] = self.NOW.isoformat()
                    params['DIRECTORY'] = params['NOW'].replace(":", "").replace("-", "")
                    resource_info = {
                        "package_id": package_name,
                        "revision_id": params['NOW'],
                        "description": "Raw Data for Calendar year " + self.NOW.strftime('%Y'),
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
                print('{} - LoadCKAN: Replacing file {} on ckan repository'.format(datetime.datetime.now(), curr_file['path']))
                cc.update_resource(self.api_key, package_name, curr_file['path'], curr_file['name'], None)

            return []
        except Exception as e:
            print ("issue : %s, file: %s\n" % (e, f))
            return [e]


