import sys
import os
import logging
import datetime
import pandas
import pyodbc
import jsonpickle
from sqlalchemy.exc import InvalidRequestError

from odmdata import Series
from odmdata import Site
from odmdata import SpatialReference
from odmdata import Qualifier
from odmdata import DataValue
from odmservices import ServiceManager

this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)

time_format = '%Y-%m-%d'
formatString = '%s  %s: %s'
service_manager = ServiceManager()
UPDATE_CACHE = True
# UPDATE_CACHE = False

issues = []

DB_CODE_LOOKUP = {
    'LR': 'iUTAH_Logan_OD',
    'BSF': 'iUTAH_Logan_OD',
    'PR': 'iUTAH_Provo_OD',
    'RB': 'iUTAH_RedButte_OD'
}

QC1_RESOURCE_ABSTRACT = 'This dataset contains quality control level 1 (QC1) data for all of the variables ' \
                        'measured for the iUTAH GAMUT Network {site_name} ({site_code}). Each file contains all ' \
                        'available QC1 data for a specific variable. Files will be updated as new data become ' \
                        'available, but no more than once daily. These data have passed QA/QC procedures such as ' \
                        'sensor calibration and visual inspection and removal of obvious errors. These data are ' \
                        'approved by Technicians as the best available version of the data. See published script ' \
                        'for correction steps specific to this data series. Each file header contains detailed ' \
                        'metadata for site information, variable and method information, source information, and ' \
                        'qualifiers referenced in the data.'

RAW_RESOURCE_ABSTRACT = 'This dataset contains raw data for all of the variables ' \
                        'measured for the iUTAH GAMUT Network {site_name} ({site_code}). Each file contains a ' \
                        'calendar year of data. The file for the current year is updated on a daily basis. ' \
                        'The data values were collected by a variety of sensors at 15 minute intervals. ' \
                        'The file header contains detailed metadata for site and the variable and method ' \
                        'of each column.'

contributors = [
    {"contributor": {"name": "Zach Aanderud", "organization": "Brigham Young University"}},
    {"contributor": {"name": "Michelle Baker", "organization": "Utah State University"}},
    {"contributor": {"name": "Dave Bowling", "organization": "University of Utah"}},
    {"contributor": {"name": "Jobie Carlile", "organization": "Utah State University"}},
    {"contributor": {"name": "Chris Cox", "organization": "Utah State University"}},
    {"contributor": {"name": "Joe Crawford", "organization": "Brigham Young University"}},
    {"contributor": {"name": "Dylan Dastrup", "organization": "Brigham Young University"}},
    {"contributor": {"name": "Jim Ehleringer", "organization": "University of Utah"}},
    {"contributor": {"name": "Dave Eiriksson", "organization": "University of Utah"}},
    {"contributor": {"name": "Jeffery S. Horsburgh", "organization": "Utah State University", "address": "Utah US",
                     "phone": "(435) 797-2946"}},
    {"contributor": {"name": "Amber Spackman Jones", "organization": "Utah State University"}},
    {"contributor": {"name": "Scott Jones", "organization": "Utah State University"}}]


class GenericResourceDetails:
    def __init__(self):
        self.resource_name = ''
        self.abstract = ''
        self.keywords = []
        self.creators = []
        self.metadata = []
        self.temporal_start = None
        self.temporal_end = None
        self.coord_units = 'Decimal Degrees'
        self.geo_projection = None
        self.lat = None
        self.lon = None

        self.credits = None

    def getMetadata(self):
        # return self.metadata.encode('utf-8').replace('\'', '"')
        return str(self.metadata).replace('\'', '"')

def getNewRawDataResourceInformation(site_code, valid_files=None):
    """

    :param site_code: The site code, used to get site details from the iutahdbs server
    :type site_code: str
    :param valid_files: File Details for the files we will be uploading to the resource
    :type valid_files: list of FileDetails
    :return:
    :rtype:
    """
    db_code = site_code.split('_')[0]
    service_manager._current_connection = {'engine': 'mssql', 'user': 'webapplication', 'password': 'W3bAppl1c4t10n!',
                                           'address': 'iutahdbs.uwrl.usu.edu', 'db': DB_CODE_LOOKUP[db_code]}
    series_service = service_manager.get_series_service()
    site = series_service.get_site_by_code(site_code)  # type: Site
    new_resource = GenericResourceDetails()
    new_resource.resource_name = "iUTAH GAMUT Network Raw Data at {site_name} ({site_code})".format(site_name=site.name,
                                                                                                    site_code=site.code)
    new_resource.abstract = RAW_RESOURCE_ABSTRACT.format(site_name=site.name, site_code=site.code)
    new_resource.keywords = [site.name, site.type, 'time series', 'iUTAH', 'GAMUT', 'raw data']
    if valid_files is not None and len(valid_files) > 0:
        variables = set([v.variable_names.replace(',', ' -') for v in valid_files if len(v.variable_names) > 0])
        new_resource.keywords.extend(list(variables))
        coverage_start_list = [v.coverage_start for v in valid_files if len(v.variable_names) > 0]
        coverage_end_list = [v.coverage_end for v in valid_files if len(v.variable_names) > 0]
        start_cov = min(coverage_start_list) if len(coverage_start_list) > 0 else None
        end_cov = max(coverage_end_list) if len(coverage_end_list) > 0 else None
        if start_cov is not None and end_cov is not None:
            temporal_data = {"coverage":
                             {"type": "period",
                              "value": {"start": start_cov.strftime(time_format),
                                        "end": end_cov.strftime(time_format)}}}
            new_resource.metadata.append(temporal_data)

    # Add Credits
    credit_dict = {'fundingagency':
                   {'agency_name': 'National Science Foundation',
                                   'award_title': 'iUTAH-innovative Urban Transitions and Aridregion Hydro-sustainability',
                                   'award_number': '1208732',
                                   'agency_url': 'http://www.nsf.gov'}}
    new_resource.metadata.append(credit_dict)

    authors = {"creator": {"organization": 'iUTAH GAMUT Working Group'}}
    # authors = {"creator": {"name": 'iUTAH GAMUT Working Group', 'organization': 'iUtah'}}
    new_resource.metadata.append(authors)

    spatial_coverage = dict(coverage={'type': 'point',
                                      'value': {
                                          'east': '{}'.format(site.longitude),
                                          'north': '{}'.format(site.latitude),
                                          'units': 'Decimal degrees',
                                          'name': '{}'.format(site.name),
                                          'elevation': '{}'.format(site.elevation_m),
                                          'projection': '{}'.format(site.spatial_ref.srs_name)
                                      }})
    new_resource.metadata.append(spatial_coverage)

    for contrib in contributors:
        new_resource.metadata.append(contrib)

    return new_resource


class FileDetails(object):
    def __init__(self, site_code=None, site_name=None, file_path=None, file_name=None, variable_names=None):
        self.coverage_start = None
        self.coverage_end = None
        self.file_path = "" if file_path is None else file_path
        self.file_name = "" if file_name is None else file_name
        self.site_code = "" if site_code is None else site_code
        self.site_name = "" if site_name is None else site_name
        self.variable_names = [] if variable_names is None else variable_names
        self.is_empty = True
        self.created = False

    def __str__(self):
        fd_str = '{site} - {s_name} - {f_name}'
        return fd_str.format(site=self.site_code, s_name=self.site_name, f_name=self.file_name)
