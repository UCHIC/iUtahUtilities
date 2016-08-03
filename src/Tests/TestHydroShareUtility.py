import unittest
import re

from src.UpdateTool import AUTH_FILE_PATH, dump_location, RE_SITE_CODE, RE_RESOURCE_FILTER
from src.Utilities.HydroShareUtility import HydroShareUtility, HydroShareUtilityException


def getValidCredentials():
    auth_file = open(AUTH_FILE_PATH, 'r')
    username, password = auth_file.readline().split()
    client_id, client_secret = auth_file.readline().split()
    return {'client_id': client_id, 'client_secret': client_secret, 'username': username, 'password': password}


def getSampleFileListing():
    filename_list = ['iUTAH_GAMUT_BSF_CONF_BA_RawData_2016.csv', 'iUTAH_GAMUT_LR_FB_BA_RawData_2016.csv',
                     'iUTAH_GAMUT_PR_BJ_CUWCD_RawData_2016.csv', 'iUTAH_GAMUT_PR_CH_CUWCD_RawData_2016.csv',
                     'iUTAH_GAMUT_PR_KM_B_RawData_2016.csv', 'iUTAH_GAMUT_PR_TC_CUWCD_RawData_2016.csv',
                     'iUTAH_GAMUT_PR_UM_CUWCD_RawData_2016.csv', 'iUTAH_GAMUT_PR_WD_USGS_RawData_2016.csv',
                     'iUTAH_GAMUT_PR_YL_R_RawData_2016.csv', 'iUTAH_GAMUT_RB_ARBR_USGS_RawData_2016.csv',
                     'iUTAH_GAMUT_RB_LKF_A_RawData_2016.csv', 'iUTAH_GAMUT_RB_LKF_A_RawData_2016.csv',
                     'iUTAH_GAMUT_ABC_XYZ_RawData_2016.csv']
    file_listing = []
    for item in filename_list:
        file_to_upload = dump_location + item
        result = re.match(RE_SITE_CODE, item, re.IGNORECASE)
        if result:
            file_listing.append({"path": file_to_upload, "name": item, "site": result.group(2)})
    return file_listing


class TestHydroShareUtility(unittest.TestCase):
    def setUp(self):
        self.hydroshare = HydroShareUtility()

    def test_DefaultConstructor(self):
        self.assertEquals(self.hydroshare.client, None, "Client is none")
        self.assertEquals(self.hydroshare.auth, None, "No auth details given")
        self.assertEquals(self.hydroshare.user_info, None, "User info is unknown")

    def test_AuthenticationSuccess(self):
        credentials = getValidCredentials()
        self.assertEquals(self.hydroshare.auth, None, "No auth details given")
        success = self.hydroshare.authenticate(**credentials)
        self.assertTrue(success)
        self.assertIsNot(self.hydroshare.auth, None, "Valid credentials provided")
        self.assertIsNot(self.hydroshare.user_info, None, "User information saved on authentication")

    def test_AuthenticationNoAuth(self):
        self.assertEquals(self.hydroshare.auth, None, "No auth details given")
        success = self.hydroshare.authenticate(None, None)
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")

    def test_AuthenticationMissingParams(self):
        credentials = getValidCredentials()
        self.assertEquals(self.hydroshare.auth, None, "No auth details given")
        success = self.hydroshare.authenticate("bad", "bad", credentials['client_id'], credentials['client_secret'])
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")
        success = self.hydroshare.authenticate(credentials['username'], "bad",
                                               credentials['client_id'], credentials['client_secret'])
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")
        success = self.hydroshare.authenticate("bad", credentials['password'],
                                               credentials['client_id'], credentials['client_secret'])
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")
        success = self.hydroshare.authenticate(credentials['username'], credentials['password'],
                                               "bad_id", credentials['client_secret'])
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")
        success = self.hydroshare.authenticate(credentials['username'], credentials['password'],
                                               credentials['client_id'], "bad_secret")
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")
        success = self.hydroshare.authenticate(credentials['username'], credentials['password'],
                                               credentials['client_id'], "bad_secret")
        self.assertFalse(success)
        self.assertEquals(self.hydroshare.auth, None, "No valid details given")

    def test_ResourceFilePairingNoAuth(self):
        try:
            self.hydroshare.pairFilesToResources([""])
            self.assertTrue(False, 'No exception thrown, test failed')
        except HydroShareUtilityException as e:
            self.assertIsNot(e, None)
            self.assertTrue(True, 'Exception thrown when user not authenticated')

    def test_ResourceFilter(self):
        credentials = getValidCredentials()
        self.assertTrue(self.hydroshare.authenticate(**credentials))
        all_resources = self.hydroshare.filterResourcesByRegex(".*")
        filtered_resources = self.hydroshare.filterResourcesByRegex(RE_RESOURCE_FILTER)
        self.assertGreater(len(all_resources), len(filtered_resources))

    def test_ResourcePairingWithAuth(self):
        credentials = getValidCredentials()
        self.assertTrue(self.hydroshare.authenticate(**credentials))
        pairs, unpaired = self.hydroshare.pairFilesToResources([])
        self.assertEquals(0, len(pairs))
        self.assertEquals(0, len(unpaired))

        # The following relies on HydroShare having at least one resource that matches at least one file
        valid_file_list = getSampleFileListing()
        pairs, unpaired = self.hydroshare.pairFilesToResources(valid_file_list, RE_RESOURCE_FILTER)
        self.assertGreaterEqual(len(pairs), 1)
        self.assertEquals(len(valid_file_list), len(unpaired) + len(pairs))

    def test_updateResources(self):
        credentials = getValidCredentials()
        self.assertTrue(self.hydroshare.authenticate(**credentials))
        valid_file_list = getSampleFileListing()
        pairs, unpaired = self.hydroshare.pairFilesToResources(valid_file_list, RE_RESOURCE_FILTER)
        self.assertGreaterEqual(len(pairs), 1)
        self.assertEquals(len(valid_file_list), len(unpaired) + len(pairs))
        result = self.hydroshare.upload(pairs)
        self.assertEquals(len(result), 0)
        failed_result = self.hydroshare.upload(unpaired)
        self.assertGreater(len(failed_result), 0)
