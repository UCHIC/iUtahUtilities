import re

from hs_restclient import *
from oauthlib.oauth2 import InvalidGrantError, InvalidClientError


class HydroShareUtilityException(Exception):
    def __init__(self, args):
        super(HydroShareUtilityException, self).__init__(args)


class HydroShareUtility:
    def __init__(self):
        self.client = None
        self.auth = None
        self.user_info = None

    def authenticate(self, username, password, client_id=None, client_secret=None):
        """
        Authenticates access to allow read/write access to privileged resources
        :param username: username for HydroShare.org
        :param password: password associated with username
        :param client_id: Client ID obtained from HydroShare
        :param client_secret: Client Secret provided by HydroShare
        :return: Returns true if authentication was successful, false otherwise
        """
        if client_id is not None and client_secret is not None:
            self.auth = HydroShareAuthOAuth2(client_id, client_secret, username=username, password=password)
        else:
            self.auth = HydroShareAuthBasic(username, password)
        try:
            self.client = HydroShare(auth=self.auth)
            self.user_info = self.client.getUserInfo()
            return True
        except HydroShareException as e:  # for incorrect username/password combinations
            print('Authentication failed: {}'.format(e))
        except InvalidGrantError as e:    # for failures when attempting to use OAuth2
            print('Credentials could not be validated: {}'.format(e))
        except InvalidClientError as e:
            print('Invalid client ID and/or client secret: {}'.format(e))
        self.auth = None
        return False

    def purgeDuplicates(self, local_file, file_list, resource, confirm_delete=False):
        shorter_name = os.path.basename(local_file['name'])
        just_the_name = shorter_name[:-4]
        for server_file in file_list:
            server_file_name = os.path.basename(server_file)
            if shorter_name == server_file_name:
                print('Exact match: {}'.format(shorter_name))
            elif just_the_name in server_file_name:
                delete_me = confirm_delete
                if confirm_delete:
                    user_answer = raw_input("Delete file {} [Y/n]: ".format(server_file_name))
                    if user_answer != 'N' or user_answer != 'n':
                        delete_me = True
                    else:
                        delete_me = False

                if delete_me or not confirm_delete:
                    self.client.deleteResourceFile(resource['resource_id'], server_file_name)
                    print('Deleting file {}...'.format(server_file_name))
                else:
                    print('Skipping file {}...'.format(server_file_name))
            elif re.search('{}\%20\([0-9]+\)'.format(just_the_name), server_file_name):
                print('Found another duplicate: {}'.format(server_file_name))
            else:
                print('Not flagged as dup: {}'.format(server_file_name))


    def pairFilesToResources(self, file_list, resource_regex_filter=None, regex_flags=re.I):
        """
        Given a list of files and optional global filter, find a resource that matches the site code of each file
        :param get_unmatched: If true, returns a list of matched and a list of unmatched files, otherwise only
                                 returns the matched files
        :param file_list: List of file dictionaries in format: {'path': path, 'name': log_file, 'site': site_code }
        :param resource_regex_filter: Regex filter initially applied before checking file/resource pairs
        :param regex_flags: Default flag is "ignorecase", but any valid flags can be specified
        :return: Returns matched and unmatched files dictionary lists in form [{'resource': resource, 'file', file_dict,
                 'overwrite_remote': True/False }, { ... } ]
        """
        filtered_resources = self.filterResourcesByRegex(resource_regex_filter, regex_flags)
        matched_files = []
        unmatched_files = []
        for local_file in file_list:
            found_match = False
            for resource in filtered_resources:
                if not re.search(local_file['site'], resource['resource_title'], re.IGNORECASE):
                    continue
                resource_files = self.client.getResourceFileList(resource['resource_id'])
                file_list = []
                for resource_file in resource_files:
                    file_list.append(resource_file['url'])
                if False:  # Use this to clean out the extra files you accidentally created during testing
                    self.purgeDuplicates(local_file, file_list, resource, True)

                duplicates = len([remote_file for remote_file in file_list if local_file['name'] in remote_file])
                matched_files.append({'resource': resource, 'file': local_file, 'overwrite_remote': duplicates})
                found_match = True
                break
            if not found_match:
                unmatched_files.append(local_file)
        return matched_files, unmatched_files

    def filterResourcesByRegex(self, regex_string, regex_flags=re.IGNORECASE):
        """
        Apply a regex filter to all available resources. Useful for finding GAMUT resources
        :param regex_string: String to be used as the regex filter
        :param regex_flags: Flags to be passed to the regex search
        :return: A list of resources that matched the filter
        """
        if self.auth is None:
            raise HydroShareUtilityException("Cannot query resources without authentication")
        all_resources = self.client.getResourceList()
        if regex_string is None:
            return all_resources
        filtered_resources = []
        regex_filter = re.compile(regex_string, regex_flags)
        for resource in all_resources:
            if regex_filter.search(resource['resource_title']) is not None:
                filtered_resources.append(resource)
        return filtered_resources

    def upload(self, paired_file_list, retry_on_failure=True):
        """
        Connect as user and upload the files to HydroShare
        :param paired_file_list: List of dictionaries in format [ {"name": "file_name", "path": "file_path" }, {...} ]
        :param retry_on_failure: If an exception occurs in this function, this function will call itself once more
        :return: An error string on multiple failures, and nothing on success
        """
        if self.auth is None:
            raise HydroShareUtilityException("Cannot modify resources without authentication")
        try:
            for pair in paired_file_list:
                resource = pair['resource']
                local_file = pair['file']
                action_str = 'created'
                if pair['overwrite_remote']:
                    action_str = 'updated'
                    self.client.deleteResourceFile(resource['resource_id'], local_file['name'])
                self.client.addResourceFile(resource['resource_id'], local_file['path'])
                print("{} {} in resource {}".format(local_file['path'], action_str, resource['resource_title']))
        except HydroShareException as e:
            if retry_on_failure:
                print('Initial upload encountered an error - attempting again. Error encountered: \n{}'.format(e.message))
                return self.upload(paired_file_list, retry_on_failure=False)
            else:
                return ["Upload retry failed - could not complete upload to HydroShare due to exception: {}".format(e)]
        except KeyError as e:
            return ['Incorrectly formatted arguments given. Expected key not found: {}'.format(e)]
        return []
