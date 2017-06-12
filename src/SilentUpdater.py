"""

Tool for updating iUtah GAMUT data in HydroShare and CKAN repositories

"""

"""



    HydroShare auth details

    Dataset details:
        Files to generate
            Series partitioning things
        HydroShare resource to upload to

"""

import datetime
import os
import re
import smtplib
import sys
import json
from Utilities.DatasetGenerator import *
from pubsub import pub


# __title__ = 'iUtahUtilities Update Tool'
WINDOWS_OS = 'nt' in os.name
DIR_SYMBOL = '\\' if WINDOWS_OS else '/'
PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(PROJECT_DIR))

from GAMUTRawData.CSVDataFileGenerator import *
from exceptions import IOError
from Utilities.HydroShareUtility import HydroShareUtility, HydroShareException, HydroShareUtilityException
from Utilities.CkanUtility import CkanUtility


file_path = '{root}{slash}GAMUT_CSV_Files{slash}'.format(root=PROJECT_DIR, slash=DIR_SYMBOL)
log_file = '{file_path}csvgenerator.log'.format(file_path=file_path)
series_dump_location = file_path + 'SeriesFiles/{series}/'


class Arguments:
    """
    Class for defining and parsing command line arguments
    """

    def __init__(self, args):
        self.verbose = False
        self.debug = False
        self.op_file_path = './operations_file.json'
        for arg in args:
            if '--verbose' in arg:
                self.verbose = True
            elif '--file=' in arg:
                self.op_file_path = arg.split('--file=')[1]
            elif '--debug' in arg:
                self.debug = True


    def print_usage_info(self):
        help_string = ("\nLoadCKAN Tool" +
                       "\n   --file=<path>                  Absolute or relative path of operations file" +
                       "\n   --debug                        Not currently used" +
                       "\n   --verbose                      Prints to stdout as well as to log file")
        original_output = None
        if not sys.__stdout__ == sys.stdout:
            print(help_string)
            original_output = sys.stdout
            sys.stdout = sys.__stdout__
        print(help_string)
        print(sys.argv)
        if original_output is not None:
            sys.stdout = original_output


class Logger(object):
    """
    Overrides Python print function and maintains the program log file
    """

    def __init__(self, logfile, overwrite=False):
        self.terminal = sys.stdout
        if overwrite or not os.path.exists(logfile):
            mode = 'w'
        else:
            mode = 'a'
        self.log = open(logfile, mode=mode)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)


def uploadToHydroShare(user_auth, sites, resource_regex, file_regex, resource_generator=None):
    """
    :param resource_generator: For sites without resources, call this function to get the resource details
    :type resource_generator: function
    :param file_regex: Regular expression string used to break down the file name into useable parts
    :type file_regex: str
    :param user_auth: Authentication details
    :type user_auth: dict
    :param sites: Dictionary of sites with site files
    :type sites: dict of list of FileDetails
    :param resource_regex:
    :type resource_regex: str
    :return:
    :rtype:
    """
    hydroshare = HydroShareUtility()
    if hydroshare.authenticate(**user_auth):
        print("Successfully authenticated. Getting resource_cache and checking for duplicated files")
        discovered_resources = hydroshare.filterResourcesByRegex(resource_regex)

        bad_resources = []

        for resource in discovered_resources:
            print 'Resource: {}'.format(resource)

        for resource_id in discovered_resources:
            # resource_id = resource_info['resource_id']
            # resource_title = resource_info['resource_title']
            try:
                hydroshare.purgeDuplicateGamutFiles(resource_id, file_regex)
                # good_resources.append((resource_id, resource_title))
            except: # Exception as e:
                # bad_resources.append((resource_id, resource_title))
                # discovered_resources.remove(resource_id)
                pass

        # print "Originally discovered {} resources".format(len(good_resources))
        #
        # print "Resources that throw an error while fetching a file list: "
        # for resource in bad_resources:
        #     print resource
        # print ""
        #
        # print "Valid resources remaining are listed below: "
        # for resource in good_resources:
        #     print resource
        # print ""
        #
        # print "After removing {} failed resources, we have {} resources remaining".format(len(bad_resources), len(good_resources))
        #

        # Check for matching resources for each site - we can't update a resource if we don't know what it is
        paired_sites, unpaired_sites = hydroshare.pairSitesToResources(sites.keys(), discovered_resources)

        # Create new resources if needed, and add the new resource to the site/resource pair list
        if resource_generator is not None:
            print 'Creating any missing resources'
            for site_code in unpaired_sites:
                valid_files = [f for f in sites[site_code] if not f.is_empty]
                if len(valid_files) == 0:
                    continue
                resource_details = resource_generator(site_code, valid_files)
                print 'Creating new resource {}'.format(resource_details.resource_name)
                resource_id = hydroshare.createNewResource(resource_details)
                paired_sites.append({'resource_id': resource_id, 'site_code': site_code})
                unpaired_sites.remove(site_code)

        print 'Performing file operations for {} resources'.format(len(paired_sites))
        # Upload new, proper files - delete files that have been uploaded and are empty
        for pair in paired_sites:
            site_code = pair['site_code']
            hydroshare.removeResourceFiles([f for f in sites[site_code] if f.is_empty], pair['resource_id'])
            success = hydroshare.upload([f for f in sites[site_code] if not f.is_empty], pair['resource_id'])
            if not success:
                bad_resources.append('https://www.hydroshare.org/resource/{}/'.format(pair['resource_id']))

        print 'Resources that were unable to update: \n{}\n'.format(bad_resources)

        # Make sure our resources are public, this has potential to change if a resource has only one file
        hydroshare.setResourcesAsPublic(discovered_resources)

        # And we're done - let's report our results
        paired_site_codes = [item['site_code'] for item in paired_sites]
        print('{}/{} resource_cache found: {}'.format(len(paired_site_codes), len(sites.keys()), paired_site_codes))
        print 'The following sites have no valid files and/or no target resource: {}'.format(unpaired_sites)

        # Set to true if you want to create a site/resource_url map for known Resources
        pair_dict = {}
        for pair in paired_sites:
            pair_dict[pair['site_code']] = 'https://www.hydroshare.org/resource/{}/'.format(pair['resource_id'])

        # # Delete invalid QC1 Resources
        # if resource_regex == RE_QC1_RESOURCES:
        #     discovered_resources = hydroshare.filterOwnedResourcesByRegex(RE_QC1_RESOURCES)
        #     for resource_id in discovered_resources:
        #         file_list = hydroshare.getResourceFileList(resource_id, refresh_cache=True)
        #         # Start delete here
        #         for remote_file in file_list:
        #             print remote_file['url']
        #             if re.match(RE_RAW_FILE, remote_file['url'], re.IGNORECASE):
        #                 hydroshare.deleteResource(resource_id, confirm=False)
        #         # End delete here
        #         if len(file_list) == 0:
        #             hydroshare.deleteResource(resource_id, confirm=False)

        # Delete any empty resources - double checking to ensure we didn't make any new ones
        # discovered_resources = hydroshare.filterOwnedResourcesByRegex(resource_regex)
        # for resource_id in discovered_resources:
        #     file_list = hydroshare.getResourceFileList(resource_id, refresh_cache=True)
        #     if len(file_list) == 0:
        #         hydroshare.deleteResource(resource_id, confirm=False)

        return pair_dict


def build_dirs(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


if False and __name__ == "__main__":
    user_args = Arguments(sys.argv)
    build_dirs(file_path)
    if user_args.verbose or True:
        sys.stdout = Logger(log_file, overwrite=True)
    else:
        sys.stdout = open(log_file, 'w')

    actions = ActionManager()
    operations = actions.LoadData(user_args.op_file_path)
    if operations is None:
        print('Error in loading actions from file {} - program exiting'.format(user_args.op_file_path))
        exit()

    # Get valid connections
    start_time = datetime.datetime.now()

    hs_connections = operations.GetValidHydroShareConnections()

    print 'HydroShare connections verified in {} seconds. ' \
          'Validating ODM connections'.format(datetime.datetime.now() - start_time)
    start_time = datetime.datetime.now()

    odm_connections = operations.GetValidOdmConnections()

    print 'ODM connections verified in {} seconds'.format(datetime.datetime.now() - start_time)

    print hs_connections
    print odm_connections

    # Go through each dataset

    for dataset in operations.Datasets:                         # type: H2ODataset
        print('Creating series files for dataset: {}').format(dataset)
        increment_time = datetime.datetime.now()

        # Make sure HydroShare and odm_connections are valid and exist

        # After that, send to dataset generator with odm_connection and with series numbers, options


        print 'Raw files updated - time taken: {}'.format(datetime.datetime.now() - increment_time)

    #
    # # Update the local Raw Data files
    # raw_files = dataParser(raw_dump_location, 'Raw', curr_year)
    #
    # # Update the local Quality Control Level 1 files
    # qc_files = dataParser(qc_dump_location, 'QC', curr_year)
    #
    # # Start the upload process to Hydroshare
    # print "\nRAW:"
    # stopwatch_timer = datetime.datetime.now()
    # raw_pairs = uploadToHydroShare(settings['hydroshare_auth'], raw_files, RE_RAW_RESOURCES, RE_RAW_FILE, resource_generator=getNewRawDataResourceInformation)
    # print 'Raw files uploaded - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)
    # print "\n\nQC:"
    # stopwatch_timer = datetime.datetime.now()
    # qc1_pairs = uploadToHydroShare(settings['hydroshare_auth'], qc_files, RE_QC1_RESOURCES, RE_QC1_FILE, resource_generator=getNewQC1ResourceInformation)
    # print 'QC Level 1 files uploaded - time taken: {}'.format(datetime.datetime.now() - stopwatch_timer)
    #
    # all_sites = set(qc1_pairs.keys() + raw_pairs.keys())
    # link_dict = {}
    # for site in all_sites:
    #     link_dict[site] = {}
    #     if site in qc1_pairs.keys():
    #         link_dict[site]['controlled'] = qc1_pairs[site]
    #     if site in raw_pairs.keys():
    #         link_dict[site]['raw'] = raw_pairs[site]

    # print '\nvar linkMap = {}'.format(link_dict)
    # print 'Program finished running - total time: {}'.format(datetime.datetime.now() - start_time)


