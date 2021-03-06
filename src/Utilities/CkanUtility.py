"""
Calling Format:
>python iutah_ckan_client.py update_resource 'value for api_key' *name of the dataset* 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
"""

import datetime
import CKANClient.iutah_ckan_client as cc

from GAMUTRawData.CSVDataFileGenerator import FileDetails

class CkanUtility:
    def __init__(self, api_key, dump_location):
        self.address = 'http://repository.iutahepscor.org'
        self.NOW = datetime.datetime.now()
        self.FORMAT_STRING = '%s  %s: %s'
        self.api_key = api_key
        self.dump_location = dump_location

    def upload(self, file_list):
        """

        :param file_list: FileDetails dictionary, with Site_Code as keys
        :type file_list: dict of FileDetails
        :return: List of issues encountered
        :rtype: list of str
        """
        res = cc.get_package_list(self.api_key)
        issue_list = []
        for site_code in file_list.keys():
            for curr_file in file_list[site_code]:
                try:
                    package_name = ""
                    site_code_formatted = curr_file.site_code.lower().replace('_', '-')
                    for r in res:
                        if site_code_formatted in r:
                            package_name = r
                            break

                    if len(package_name) == 0:
                        issue_list.append('Unable to find match for site {}'.format(curr_file.site_code))
                        continue

                    if self.NOW.strftime('%m %d') == "01 01":  # if this is jan 1 of a new year
                        params = {}
                        params['CKAN_APIKEY'] = self.api_key
                        params['FILENAME'] = curr_file.file_name
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

                    print('{} - LoadCKAN: Replacing CKAN file {}'.format(datetime.datetime.now(), curr_file.file_path))
                    cc.update_resource(api_key=self.api_key, package_name=package_name,
                                       file_to_upload=curr_file.file_path, replace_file_name=curr_file.file_name,
                                       resource_info=None)
                except Exception as e:
                    print ("issue : %s, file: %s\n" % (e, curr_file))
                    issue_list.append("issue : %s, file: %s\n" % (e, curr_file))
        return issue_list


