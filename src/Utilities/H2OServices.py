
import datetime
import os
import re
import smtplib
import sys
import json
from Utilities.DatasetGenerator import *
from pubsub import pub
import time
import wx

from threading import Thread

from GAMUTRawData.odmservices import ServiceManager
from Utilities.DatasetGenerator import OdmDatasetConnection, H2ODataset
from Utilities.HydroShareUtility import HydroShareAccountDetails, HydroShareUtility, ResourceTemplate
from Utilities.Odm2Wrapper import *

from GAMUTRawData.CSVDataFileGenerator import *
from Utilities.DatasetGenerator import *
from exceptions import IOError
from Utilities.HydroShareUtility import HydroShareUtility, HydroShareException, HydroShareUtilityException


__title__ = 'H2O Service'
WINDOWS_OS = 'nt' in os.name
DIR_SYMBOL = '\\' if WINDOWS_OS else '/'
PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.dirname(PROJECT_DIR))

use_debug_file_naming_conventions = True



class H2ODefaults:
    SETTINGS_FILE_NAME = './operations_file.json'.format()
    PROJECT_DIR = '{}'.format(os.path.dirname(os.path.realpath(__file__)))
    DATASET_DIR = '{}/H2O_dataset_files/'.format(PROJECT_DIR)
    LOGFILE_DIR = '{}/../logs/'.format(PROJECT_DIR)
    GUI_PUBLICATIONS = {
        'logger': lambda message: {'message': message},
        'Dataset_Started': lambda done, total, name: {'message': '{}/{}: Creating dataset {}'.format(done, total, name)},
        'Dataset_Generated': lambda done, total, name: {'message': '{}/{}: Generated dataset {}'.format(done, total, name)}
    }

class H2OLogger:
    def __init__(self, logfile_dir=H2ODefaults.LOGFILE_DIR, log_to_gui=False):
        self.log_to_gui = log_to_gui
        self.terminal = sys.stdout
        if use_debug_file_naming_conventions:
            file_name = '{}/H2O_Log_{}.csv'.format(logfile_dir, 'TestFile')
        else:
            file_name = '{}/H2O_Log_{}.csv'.format(logfile_dir, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        self.LogFile = open(file_name, mode='w')

    def write(self, message):
        self.terminal.write(message)
        self.LogFile.write(message)
        # if self.log_to_gui:
        #     pub.sendMessage('logger', message=message)

class H2OService:
    def __init__(self, hydroshare_connections=None, odm_connections=None, resource_templates=None, datasets=None,
                 subscriptions=None):
        self.HydroShareConnections = hydroshare_connections if hydroshare_connections is not None else {}  # type: dict[str, HydroShareAccountDetails]
        self.DatabaseConnections = odm_connections if odm_connections is not None else {}  # type: dict[str, OdmDatasetConnection]
        self.ResourceTemplates = resource_templates if resource_templates is not None else {}  # type: dict[str, ResourceTemplate]
        self.Datasets = datasets if datasets is not None else {}  # type: dict[str, H2ODataset]
        self.Subscriptions = subscriptions if subscriptions is not None else [] # type: list[str]

        self._initialize_directories([H2ODefaults.DATASET_DIR, H2ODefaults.LOGFILE_DIR])
        sys.stdout = H2OLogger(log_to_gui='logger' in self.Subscriptions)

        self.ThreadedFunction = None # type: Thread
        self.ThreadKiller = ['Continue']

    def _thread_checkpoint(self):
        return self.ThreadKiller[0] == 'Continue'

    def _threaded_dataset_generation(self):
        generated_files = [] # type: list[FileDetails]

        dataset_count = len(self.Datasets)
        current_dataset = 0
        for name, dataset in self.Datasets.iteritems():
            self._thread_checkpoint()

            current_dataset += 1
            self.NotifyVisualH20('Dataset_Started', current_dataset, dataset_count, dataset.name)

            odm_service = ServiceManager()
            odm_service._current_connection = self.DatabaseConnections[dataset.odm_db_name].ToDict()
            series_service = odm_service.get_series_service()

            series_list = [series_service.get_series_by_id(id) for id in dataset.odm_series]  # type: Series
            cols_to_use = DatasetHelper.GetCsvColumns(series_list)
            print 'Dataset: {}\n{}\n'.format(dataset.name, cols_to_use)

            self.NotifyVisualH20('Dataset_Generated', current_dataset, dataset_count, dataset.name)


    # Write series to their own files

    # Write series to one file

    # Chunk files by year

    #


    def StopActions(self):
        if self.ThreadedFunction is not None: # and self.ThreadedFunction.is_alive():
            self.ThreadedFunction.join(1)
            self.ThreadKiller = None

    def GenerateDatasetFiles(self, blocking=False):
        if blocking:
            return self._threaded_dataset_generation()
        if self.ThreadedFunction is not None and self.ThreadedFunction.is_alive():
            self.ThreadedFunction.join(3)
        self.ThreadKiller = ['Continue']
        self.ThreadedFunction = Thread(target=self._threaded_dataset_generation)
        self.ThreadedFunction.start()

    def UploadDatasetsToHydroShare(self, blocking=False):
        # if blocking:
        #     return
        if self.ThreadedFunction is not None and self.ThreadedFunction.is_alive():
            self.ThreadedFunction.join(3)
        self.ThreadKiller = ['Continue']
        self.ThreadedFunction = Thread(target=self._threaded_dataset_generation)
        self.ThreadedFunction.start()

    def NotifyVisualH20(self, pub_key, *args):
        if pub_key in self.Subscriptions and pub_key in H2ODefaults.GUI_PUBLICATIONS.keys():
            result = H2ODefaults.GUI_PUBLICATIONS[pub_key](*args)
            pub.sendMessage(pub_key, **result)
        # else:
        #     print('We can\'t publish {}, no one is subscribed'.format(pub_key))

    def to_json(self):
        return {'odm_connections': self.DatabaseConnections,
                'hydroshare_connections': self.HydroShareConnections,
                'resource_templates': self.ResourceTemplates,
                'datasets': self.Datasets}

    def SaveData(self, output_file=H2ODefaults.SETTINGS_FILE_NAME):
        try:
            json_out = open(output_file, 'w')
            json_out.write(jsonpickle.encode(self.to_json()))
            json_out.close()
            print('Dataset information successfully saved to {}'.format(output_file))
            return True
        except IOError as e:
            print 'Error saving to disk - file name {}\n{}'.format(output_file, e)
            return False

    def LoadData(self, input_file=H2ODefaults.SETTINGS_FILE_NAME):
        try:
            json_in = open(input_file, 'r')
            data = jsonpickle.decode(json_in.read())
            if data is not None:
                self.HydroShareConnections = data['hydroshare_connections'] if 'hydroshare_connections' in data else {}
                self.DatabaseConnections = data['odm_connections'] if 'odm_connections' in data else {}
                self.ResourceTemplates = data['resource_templates'] if 'resource_templates' in data else {}
                self.Datasets = data['datasets'] if 'datasets' in data else {}
            json_in.close()
            print('Dataset information loaded from {}'.format(input_file))
            return True
        except IOError as e:
            print 'Error reading input file data from {}:\n\t{}'.format(input_file, e)
            return False

    def _initialize_directories(self, directory_list):
        for dir_name in directory_list:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)

    def GetValidHydroShareConnections(self):
        valid_hydroshare_connections = {}
        for name, account in self.HydroShareConnections.iteritems():
            hydroshare = HydroShareUtility()
            if hydroshare.authenticate(**account.to_dict()):
                valid_hydroshare_connections[name] = account
        return valid_hydroshare_connections

    def GetValidOdmConnections(self):
        valid_odm_connections = {}
        for name, connection in self.DatabaseConnections.iteritems():
            if connection.VerifyConnection():
                valid_odm_connections[name] = connection
        return valid_odm_connections
