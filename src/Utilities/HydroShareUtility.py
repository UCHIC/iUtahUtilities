"""
Calling Format:
>python iutah_ckan_client.py update_resource 'value for api_key' *name of the dataset* 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv

Tried:
update_resource db567980-cgt8-9067-45678de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
update_resource 516ca1eb-f399-411f-9ba9-49310de285f3 my-original-dataset c:\\odm_site_1_2014.csv odm_site_1_2014.csv
"""

import copy
import datetime
import os
import smtplib
import sys
import re

from hs_restclient import *


class HydroShareUtility:
    def __init__(self):
        self.client = None
        self.auth = None
        # self.username = None
        # self.password = None
        # self.client_id = None
        # self.client_secret = None

        self.user_info = None
        self.all_resources = []
        self.filtered_resources = []
        self.resource_file_pairs = []

    def authenticate(self, user, password, client_id=None, client_secret=None):
        """
        Authenticates access to allow read/write access to privileged resources
        :param user: username for HydroShare.org
        :param password: password associated with username
        :param client_id: Client ID obtained from HydroShare
        :param client_secret: Client Secret provided by HydroShare
        :return: Returns true if authentication was successful, false otherwise
        """
        if client_id is not None and client_secret is not None:
            self.auth = HydroShareAuthOAuth2(client_id, client_secret, username=user, password=password)
        else:
            self.auth = HydroShareAuthBasic(user, password)
        self.client = HydroShare(auth=self.auth)
        try:
            self.user_info = self.client.getUserInfo()
            return True
        except HydroShareHTTPException as e:
            print('Authentication failed: {}'.format(e))
            return False

    def pairFilesToResources(self, file_list):
        files_to_match = copy.deepcopy(file_list)
        matched_files = []
        resource_matches = []
        for local_file in file_list:
            for resource in self.filtered_resources:
                if not re.search(local_file['site_code'], resource['resource_title'], re.IGNORECASE):
                    continue
                resource_files = self.client.getResourceFileList(resource['resource_id'])
                file_exists = [file_name for file_name in resource_files['url'] if local_file['name'] in file_name]
                matched_files.append({'resource': resource, 'file': local_file, 'overwrite_remote': file_exists})
                files_to_match.remove(local_file)
                break

        if not len(self.resource_file_pairs) == len(file_list):
            unused_file_count = len(file_list) - len(self.resource_file_pairs)
            print('Upload locations could not be determined for {} files'.format(unused_file_count))

        return resource_matches

    def filterResourcesByRegex(self, regex_string, regex_flags=re.IGNORECASE):
        """ Apply a regex filter to all available resources. Useful for finding GAMUT resources

        :param regex_string: String to be used as the regex filter
        :param regex_flags: Flags to be passed to the regex search
        :return: The count of resources that matched the filter
        """
        if len(self.all_resources) == 0:
            self.all_resources = self.client.getResourceList()
        regex_filter = re.compile(regex_string, regex_flags)
        for resource in self.resource_list:
            if regex_filter.search(resource['resource_title']) is not None:
                self.filtered_resources.append(resource)
        return len(self.filtered_resources)

    def upload(self, file_list, retry_on_failure=True):
        """ Connect as user and upload the files to HydroShare

        :param file_list: List of dictionaries in format [ {"name": "file_name", "path": "file_path" }, {...} ]
        :param retry_on_failure: If an exception occurs in this function, this function will call itself once more

        :return: An error string on multiple failures, and nothing on success
        """
        try:
            for pair in self.resource_file_pairs:
                resource = pair['resource']
                local_file = pair['file']
                if pair['overwrite_remote'] > 0:
                    # hs.deleteResourceFile(resource['resource_id'], local_file['name'])
                    pass
                # hs.addResourceFile(resource['resource_id'], local_file['path'])
                print("{} uploaded to resource {}".format(local_file['path'], resource['resource_title']))

        except HydroShareException as e:
            if retry_on_failure:
                print('Initial upload encountered an error - attempting again. Error encountered: \n{}'.format(e.message))
                return self.upload(file_list, retry_on_failure=False)
            else:
                return "Upload retry failed - could not complete upload to HydroShare due to exception: {}".format(e)
        return []
