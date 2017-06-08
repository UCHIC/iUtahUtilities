import sys
import os
import logging
import datetime
import pandas
import pyodbc
import jsonpickle
from sqlalchemy.exc import InvalidRequestError
from multiprocessing import Process, Queue
from time import sleep
from sqlalchemy.exc import InvalidRequestError

from Utilities.HydroShareUtility import HydroShareResource

from GAMUTRawData.odmdata import Series
from GAMUTRawData.odmdata import Site
from GAMUTRawData.odmdata import SpatialReference
from GAMUTRawData.odmdata import Qualifier
from GAMUTRawData.odmdata import DataValue
from GAMUTRawData.odmservices import ServiceManager

this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)

time_format = '%Y-%m-%d'
formatString = '%s  %s: %s'
service_manager = ServiceManager()

UPDATE_CACHE = True

class FileDetails(object):
    def __init__(self, site_code="", site_name="", file_path="", file_name="", variable_names=None):
        self.coverage_start = None
        self.coverage_end = None
        self.file_path = file_path
        self.file_name = file_name
        self.site_code = site_code
        self.site_name = site_name
        self.variable_names = [] if variable_names is None else variable_names
        self.is_empty = True
        self.created = False

    def __str__(self):
        fd_str = '{site} - {s_name} - {f_name}'
        return fd_str.format(site=self.site_code, s_name=self.site_name, f_name=self.file_name)


class H2ODataset:
    def __init__(self, name='', odm_series=None, hs_resource='', odm_db_name='', chunk_by_series=False, chunk_by_year=False):
        self.name = name                                                # type: str
        self.odm_series = odm_series if odm_series is not None else {}  # type: dict # {'odm_db_name': [1, 2, 4]}
        self.hs_resource = hs_resource                                  # type: HydroShareResource
        self.odm_db_name = odm_db_name                                  # type: HydroShareResource
        self.chunk_by_series = chunk_by_series                          # type: bool
        self.chunk_by_year = chunk_by_year                              # type: bool

    def __dict__(self):
        return {'dataset_name': self.name, 'odm_series': self.odm_series, 'hs_resource': self.hs_resource,
                'chunk_by_series': self.chunk_by_series, 'chunk_by_year': self.chunk_by_year,
                'odm_db_name': self.odm_db_name}

    def __str__(self):
        return 'Dataset {} with {} series and destination resource {}'.format(self.name, len(self.odm_series), self.hs_resource)

def _OdmDatabaseConnectionTestTimed(queue):
    db_auth = queue.get(True)
    if service_manager.test_connection(db_auth):
        queue.put(True)
    else:
        queue.put(False)

class OdmDatasetUtility:
    def __init__(self, values=None):
        self.name = ""
        self.engine = ""
        self.user = ""
        self.password = ""
        self.address = ""
        self.database = ""
        self.port = ""

        if values is not None:
            self.name = values['name'] if 'name' in values else ""
            self.engine = values['engine'] if 'engine' in values else ""
            self.user = values['user'] if 'user' in values else ""
            self.password = values['password'] if 'password' in values else ""
            self.address = values['address'] if 'address' in values else ""
            self.database = values['db'] if 'db' in values else ""
            self.port = values['port'] if 'port' in values else ""

    def VerifyConnection(self):
        queue = Queue()
        result = False
        process = Process(target=_OdmDatabaseConnectionTestTimed, args=(queue,))
        try:
            process.start()
            queue.put(self.ToDict())
            sleep(2)
            result = queue.get(True, 8)
        except Exception as exc:
            print exc

        if process.is_alive():
            process.terminate()
            process.join()
        return result

    def ToDict(self):
        return {'engine': self.engine, 'user': self.user, 'password': self.password, 'address': self.address,
                'db': self.database}


def GenerateDatasetFromSeries():

    pass


def dataParser(dump_loc, data_type, year):
    """

    :param dump_loc:
    :type dump_loc: str
    :param data_type:
    :type data_type: str
    :param year:
    :type year: str
    :return:
    :rtype: dict of list of FileDetails
    """
    all_files = {}
    stored_cache = {}
    updated_files = {}
    if data_type.lower() == 'raw':
        cache_file_name = dump_loc + 'cache_raw.json'
    else:
        cache_file_name = dump_loc + 'cache_qc1.json'
    try:
        json_in = open(cache_file_name, 'r')
        stored_cache = jsonpickle.decode(json_in.read())
        json_in.close()
        if not UPDATE_CACHE:
            return stored_cache
    except IOError as e:
        print 'Error reading cached file data - Clearing files and recreating cache.\n{}'.format(e)

    print("\n========================================================\n")
    all_files.update(handleDatabaseConnection('iUTAH_Logan_OD', 'Logan', dump_loc, year, data_type, stored_cache))
    all_files.update(handleDatabaseConnection('iUTAH_Provo_OD', 'Provo', dump_loc, year, data_type, stored_cache))
    all_files.update(handleDatabaseConnection('iUTAH_RedButte_OD', 'RedButte', dump_loc, year, data_type, stored_cache))
    print("\n========================================================\n")

    try:
        json_out = open(cache_file_name, 'w')
        json_out.write(jsonpickle.encode(all_files))
        json_out.close()
    except IOError as e:
        print 'Error saving cache to disk - cache will not be used the next time this program runs\n{}'.format(e)

    for site_code in all_files.keys():
        site_files_changed = [f for f in all_files[site_code] if f.created or f.is_empty]
        if len(site_files_changed) > 0:
            updated_files[site_code] = site_files_changed
    return updated_files

def cachedVersionIsOutdated(cached_file, new_file):
    """

    :param cached_file: File cached on local disk
    :type cached_file: FileDetails
    :param new_file: Current file being created from database
    :type new_file: FileDetails
    :return: Returns true if a new file should be generated
    :rtype: bool
    """
    if cached_file is None or cached_file.coverage_start is None or cached_file.coverage_end is None:
        return True
    elif new_file.coverage_start is not None and new_file.coverage_start < cached_file.coverage_start:
        return True
    elif new_file.coverage_end is not None and new_file.coverage_end > cached_file.coverage_end:
        return True
    else:
        return False


def handleDatabaseConnection(database, location, dump_location, year, data_type, file_cache):
    """

    :param data_type:
    :type data_type: str
    :param database: Database schema to select ('iUTAH_Logan_OD', 'iUTAH_Provo_OD', 'iUTAH_RedButte_OD')
    :type database: str
    :param location: GAMUT data network ('Logan', 'Provo', or 'RedButte')
    :type location: str
    :param dump_location: Path to folder used to store CSV files
    :type dump_location: str
    :param year: Year to constrain data to
    :type year: str
    :return: Issues encountered during file generation process
    :rtype: dict of list of FileDetails
    """
    print('Started getting sites from {} at {}'.format(database, location))
    # Getting the data
    service_manager._current_connection = {'engine': 'mssql', 'user': 'webapplication', 'password': 'W3bAppl1c4t10n!',
                                           'address': 'iutahdbs.uwrl.usu.edu', 'db': database}
    series_service = service_manager.get_series_service()
    all_sites = series_service.get_all_sites()
    site_files = {}
    for site in all_sites:
        if data_type.lower() == 'raw':
            local_dataset = GenericDataset(dump_location, location, site, year, file_cache)
            series = series_service.get_series_by_site_code_year(site.code, year)
            site_files[site.code] = local_dataset.writeToFile(series_service, series)
        else:
            local_dataset = GenericDataset(dump_location, location, site, year, file_cache)
            series = series_service.get_series_by_site_and_qc_level(site.code, 1)
            site_files[site.code] = local_dataset.writeToFile(series_service, series)
    return site_files


def createFile(self, filepath):
    try:
        file_out = open(filepath, 'w')
        return file_out
    except Exception as e:
        print('---\nIssue encountered while creating a new file: \n{}\n{}\n---'.format(e, e.message))
        return None

class GenericDataset:
    def __init__(self, dump_location, location, site, year, file_cache=None):
        # type: (str, str, str, str, dict) -> QC1_CsvLocalDataset
        self.site = site
        self.network = location
        self.csv_name = 'iUTAH_GAMUT_{site}_Quality_Control_Level_1_{var}.csv'
        self.csv_site_dir = dump_location + '{site}/'
        self.file_cache = file_cache

        self.year = year
        self.start_date = '{y}-01-01 00:00:00'.format(y=year)
        self.end_date = datetime.datetime(int(year), 12, 31, 23, 55, 59)
        self.column_count = 0

        self.csv_indexes = ["LocalDateTime", "UTCOffset", "DateTimeUTC"]
        self.qualifier_columns = ["QualifierID", "QualifierCode", "QualifierDescription"]
        self.csv_columns = ["DataValue", "CensorCode", "QualifierCode"]

        self.exception_msg = " SiteName: {site}, year: {year}, Error : {error}"


    def writeToFile(self, series_service, series_list):
        """

        :param series_service: The database connection used to retrieve additional data
        :type series_service: SeriesService
        :param series_list: Series for which we attempt to make a CSV file
        :type series_list: list of Series
        :return: Issues encountered during file generation process
        :rtype: list of FileDetails
        """
        site_files = []
        try:
            # Ensure the filesystem path exists
            site_path = self.csv_site_dir.format(site=self.site.code)
            if not os.path.exists(site_path):
                os.makedirs(site_path)

            for series in series_list:
                file_name = self.csv_name.format(site=series.site_code, var=series.variable_code)
                file_info = FileDetails(site_code=series.site_code, site_name=series.site_name, file_name=file_name,
                                        file_path=site_path + file_name, variable_names=series.variable_name)

                # Get all of the DataValues for our series
                dv_raw = series_service.get_variables_by_site_id_qc(series.variable_id, series.site_id, 1)  # type:
                if not len(dv_raw) > 0:
                    print("No data value sets found for {}, {}".format(series.site_code, self.site.name))
                    continue

                # Store the coverage data so we can use it later
                file_info.coverage_start = dv_raw["LocalDateTime"].iloc[0]
                file_info.coverage_end = dv_raw["LocalDateTime"].iloc[-1]

                recreate_file = True
                cached_file = None
                if series.site_code in self.file_cache:
                    for cached in self.file_cache[series.site_code]:
                        if cached.file_path == file_info.file_path:
                            cached_file = cached
                            break
                    recreate_file = cachedVersionIsOutdated(cached_file, file_info)

                if recreate_file or True:
                    site_files.append(file_info)
                    print 'Recreating file {}'.format(file_info.file_name)
                else:
                    cached_file.created = False
                    site_files.append(cached_file)
                    print 'We are using the cached version: {}'.format(cached_file.file_name)
                    continue

                file_out = createFile(file_info.file_path)
                if file_out is None:
                    print('Unable to create output file for {}, {}'.format(series.site_code, series.variable_code))
                    continue
                file_info.created = True

                # Get the qualifiers that we use in this series, merge it with our DataValue set
                q_list = [[q.id, q.code, q.description] for q in series_service.get_qualifiers_by_series_id(series.id)]
                q_df = pandas.DataFrame(data=q_list, columns=self.qualifier_columns)
                dv_set = dv_raw.merge(q_df, how='left', on="QualifierID")  # type: pandas.DataFrame
                del dv_raw
                dv_set.set_index(self.csv_indexes, inplace=True)

                # Drop the columns that we aren't interested in, and correct any names afterwards
                for column in dv_set.columns.tolist():
                    if column not in self.csv_columns:
                        dv_set.drop(column, axis=1, inplace=True)
                dv_set.rename(columns={"DataValue": series.variable_code}, inplace=True)

                # Getting and organizing all the data
                var_data = ExpandedVariableData(series.variable, series.method)
                sourceInfo = SourceInfo()
                sourceInfo.setSourceInfo(series.source.organization, series.source.description, series.source.link,
                                         series.source.contact_name, series.source.phone, series.source.email,
                                         series.source.citation)

                # Write the header and data to the file
                file_str = self.generateHeader()
                file_str += generateSiteInformation(self.site, self.network)
                file_str += var_data.printToFile() + "#\n"
                file_str += sourceInfo.outputSourceInfo() + "#\n"
                file_str += self.generateQualifierHeader(q_list) + "#\n"
                file_out.write(file_str)
                dv_set.to_csv(file_out)
                file_out.close()
                file_info.is_empty = False
                print ('{} handleConnection: Success - created {}'.format(datetime.datetime.now(), file_info.file_name))
        except KeyError as e:
            print('---\nIssue encountered while formatting data:\nType: {}, Value: {}\n---'.format(type(e), e.message))
            print(self.exception_msg.format(site=self.site, year=self.year, error=e))
        except IOError as e:
            print('---\nIssue encountered during file operations:\nType: {}, Value: {}\n---'.format(type(e), e.message))
            print(self.exception_msg.format(site=self.site, year=self.year, error=e))
        except Exception as e:
            print('---\nUnexpected issue while gathering data:\nType: {}, Value: {}\n---'.format(type(e), e.message))
            print(self.exception_msg.format(site=self.site, year=self.year, error=e))

        return site_files


    def generateHeader(self):
        """
        :return: Returns a string to be inserted as the CSV file's header
        :rtype: str
        """
        file_str = "# ------------------------------------------------------------------------------------------\n"
        file_str += "# WARNING: The data are released on the condition that neither iUTAH nor any of its \n"
        file_str += "# participants may be held liable for any damages resulting from their use. The following \n"
        file_str += "# metadata describe the data in this file:\n"
        file_str += "# ------------------------------------------------------------------------------------------\n"
        file_str += "#\n"
        file_str += "# Quality Control Level Information\n"
        file_str += "# -----------------------------------------------\n"
        file_str += "# These data have passed QA/QC procedures such as sensor calibration and \n"
        file_str += "# visual inspection and removal of obvious errors. These data are approved \n"
        file_str += "# by Technicians as the best available version of the data. See published\n"
        file_str += "# script for correction steps specific to this data series. \n"
        file_str += "#\n"
        return file_str

    def generateQualifierHeader(self, qualifier_list):
        """
        :return: Returns a string to be inserted as the CSV qualifier header portion
        :rtype: str
        """
        sorted_list = sorted(qualifier_list, key=lambda x: x[0])
        file_str = "# Qualifier Information\n"
        file_str += "# ----------------------------------\n"
        file_str += "# Code   Description\n"
        for q_id, code, description in sorted_list:
            file_str += "# " + code.ljust(7) + description + "\n"
        file_str += "#\n"
        return file_str

def generateSiteInformation(site, network):
    """

    :param site: Site for which to generate the header string
    :type site: Site
    :param network: Network for site (e.g. Logan, RedButte, etc)
    :return: Header string
    :rtype: str
    """
    file_str = ""
    file_str += "# Site Information\n"
    file_str += "# ----------------------------------\n"
    file_str += "# Network: " + network + "\n"
    file_str += "# SiteCode: " + str(site.code) + "\n"
    file_str += "# SiteName: " + str(site.name) + "\n"
    file_str += "# Latitude: " + str(site.latitude) + "\n"
    file_str += "# Longitude: " + str(site.longitude) + "\n"
    file_str += "# LatLonDatum: " + str(site.spatial_ref.srs_name) + "\n"
    file_str += "# Elevation_m: " + str(site.elevation_m) + "\n"
    file_str += "# ElevationDatum: " + str(site.vertical_datum) + "\n"
    file_str += "# State: " + str(site.state) + "\n"
    file_str += "# County: " + str(site.county) + "\n"
    file_str += "# Comments: " + str(site.comments) + "\n"
    file_str += "# SiteType: " + str(site.type) + "\n"
    file_str += "#\n"
    return file_str


class SourceInfo:
    def __init__(self, use_citation=True):
        self.organization = ""
        self.sourceDescription = ""
        self.sourceLink = ""
        self.contactName = ""
        self.phone = ""
        self.email = ""
        self.citation = ""
        self.use_citation = use_citation

    def setSourceInfo(self, org, srcDesc, srcLnk, cntctName, phn, email, citn):
        self.organization = org
        self.sourceDescription = srcDesc
        self.sourceLink = srcLnk
        self.contactName = cntctName
        self.phone = phn
        self.email = email
        self.citation = citn

    def outputSourceInfo(self):
        outputStr = "# Source Information\n# ------------------\n"
        outputStr += self.sourceOutHelper("Organization", self.organization)
        outputStr += self.sourceOutHelper("SourceDescription", self.sourceDescription)
        outputStr += self.sourceOutHelper("SourceLink", self.sourceLink)
        outputStr += self.sourceOutHelper("ContactName", self.contactName)
        outputStr += self.sourceOutHelper("Phone", self.phone)
        outputStr += self.sourceOutHelper("Email", self.email)
        if self.use_citation:
            outputStr += self.sourceOutHelper("Citation", self.citation)
        return outputStr

    def sourceOutHelper(self, title, value):
        return "# " + title + ": " + value + "\n"


class ExpandedVariableData:
    def __init__(self, var, method):
        self.varCode = var.code
        self.varName = var.name
        self.valueType = var.value_type
        self.dataType = var.data_type
        self.gralCategory = var.general_category
        self.sampleMedium = var.sample_medium
        self.varUnitsName = var.variable_unit.name
        self.varUnitsType = var.variable_unit.type
        self.varUnitsAbbr = var.variable_unit.abbreviation
        self.noDV = int(var.no_data_value) if var.no_data_value.is_integer() else var.no_data_value
        self.timeSupport = var.time_support
        self.timeSupportUnitsAbbr = var.time_unit.abbreviation
        self.timeSupportUnitsName = var.time_unit.name
        self.timeSupportUnitsType = var.time_unit.type
        self.methodDescription = method.description
        self.methodLink = method.link if method.link is not None else "None"
        if not self.methodLink[-1:].isalnum():
            self.methodLink = self.methodLink[:-1]

    def printToFile(self):
        formatted = ""
        formatted += "# Variable and Method Information\n"
        formatted += "# ---------------------------\n"
        formatted += self.formatHelper("VariableCode", self.varCode)
        formatted += self.formatHelper("VariableName", self.varName)
        formatted += self.formatHelper("ValueType", self.valueType)
        formatted += self.formatHelper("DataType", self.dataType)
        formatted += self.formatHelper("GeneralCategory", self.gralCategory)
        formatted += self.formatHelper("SampleMedium", self.sampleMedium)
        formatted += self.formatHelper("VariableUnitsName", self.varUnitsName)
        formatted += self.formatHelper("VariableUnitsType", self.varUnitsType)
        formatted += self.formatHelper("VariableUnitsAbbreviation", self.varUnitsAbbr)
        formatted += self.formatHelper("NoDataValue", self.noDV)
        formatted += self.formatHelper("TimeSupport", self.timeSupport)
        formatted += self.formatHelper("TimeSupportUnitsAbbreviation", self.timeSupportUnitsAbbr)
        formatted += self.formatHelper("TimeSupportUnitsType", self.timeSupportUnitsType)
        formatted += self.formatHelper("TimeSupportUnitsName", self.timeSupportUnitsName)
        formatted += self.formatHelper("MethodDescription", self.methodDescription)
        formatted += self.formatHelper("MethodLink", self.methodLink)
        return formatted

    def formatHelper(self, title, var):
        formatted = "# " + title + ": " + str(var) + "\n"
        return formatted


class CompactVariableData:
    def __init__(self):
        self.var_dict = {}
        self.method_dict = {}

    def addData(self, var, method):
        self.var_dict[var.code] = (var, method)

    def printToFile(self, vars_to_print):
        formatted = ""
        formatted += "# Variable and Method Information\n"
        formatted += "# ---------------------------\n"
        for variable_code in vars_to_print:
            if variable_code not in self.var_dict:
                continue
            variable, method = self.var_dict[variable_code]
            if method.link is None:
                tempVarMethodLink = "None"
            else:
                tempVarMethodLink = method.link if method.link[-1:].isalnum() else method.link[-1:]

            formatted += "# "
            formatted += self.formatHelper("VariableCode", variable.code)
            formatted += self.formatHelper("VariableName", variable.name)
            formatted += self.formatHelper("ValueType", variable.value_type)
            formatted += self.formatHelper("DataType", variable.data_type)
            formatted += self.formatHelper("GeneralCategory", variable.general_category)
            formatted += self.formatHelper("SampleMedium", variable.sample_medium)
            formatted += self.formatHelper("VariableUnitsName", variable.variable_unit.name)
            formatted += self.formatHelper("VariableUnitsType", variable.variable_unit.type)
            formatted += self.formatHelper("VariableUnitsAbbreviation", variable.variable_unit.abbreviation)
            formatted += self.formatHelper("NoDataValue", variable.no_data_value)
            formatted += self.formatHelper("TimeSupport", variable.time_support)
            formatted += self.formatHelper("TimeSupportUnitsAbbreviation", variable.time_unit.abbreviation)
            formatted += self.formatHelper("TimeSupportUnitsName", variable.time_unit.name)
            formatted += self.formatHelper("TimeSupportUnitsType", variable.time_unit.type)
            formatted += self.formatHelper("MethodDescription", method.description)
            formatted += self.formatHelper("MethodLink", tempVarMethodLink)[:-2] + "\n"
        return formatted

    def formatHelper(self, title, var):
        formatted = title + ": " + str(var) + " | "
        return formatted
