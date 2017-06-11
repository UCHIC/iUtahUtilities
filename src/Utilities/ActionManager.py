
from collections import defaultdict

import datetime
import os
import re
import smtplib
import sys
from collections import defaultdict
from functools import partial

import wx
import wx.dataview
import wx.grid
import jsonpickle
# import wx.lib.pubsub.pub as Publisher
from pubsub import pub
from Utilities.HydroShareUtility import HydroShareAccountDetails, HydroShareUtility, ResourceTemplate
from Utilities.DatasetGenerator import OdmDatasetUtility, H2ODataset
from Utilities.Odm2Wrapper import *
from GAMUTRawData.odmservices import ServiceManager

PERSIST_OP_FILE = './operations_file.json'
service_manager = ServiceManager()

def GetActionsFromFile(file_path):
    try:
        json_in = open(file_path, 'r')
        data = jsonpickle.decode(json_in.read())
        json_in.close()
        action_manager = ActionManager(**data)
        action_manager.__output__file = file_path
        return action_manager
    except IOError as e:
        print 'Error reading file actions data - Check your file path and try again\n{}'.format(e)
        return None

class ActionManager:
    def __init__(self, hydroshare_connections=None, odm_connections=None, resource_templates=None, datasets=None, outfile=None):
        self.HydroShareConnections = hydroshare_connections if hydroshare_connections is not None else {}   # type: dict[str, HydroShareAccountDetails]
        self.DatabaseConnections = odm_connections if odm_connections is not None else {}                   # type: dict[str, OdmDatasetUtility]
        self.ResourceTemplates = resource_templates if resource_templates is not None else {}               # type: dict[str, ResourceTemplate]
        self.Datasets = datasets if datasets is not None else {}                                            # type: dict[str, H2ODataset]
        self.__output__file = PERSIST_OP_FILE if outfile is None else outfile

    def __str__(self):
        return 'Actions file {}'.format(self.__output__file)

    def to_json(self):
        return {'odm_connections': self.DatabaseConnections,
                'hydroshare_connections': self.HydroShareConnections,
                'resource_templates': self.ResourceTemplates,
                'datasets': self.Datasets}

    def SaveData(self, new_file_path=None):
        if new_file_path is None:
            new_file_path = self.__output__file
        try:
            json_out = open(new_file_path, 'w')
            json_out.write(jsonpickle.encode(self.to_json()))
            json_out.close()
        except IOError as e:
            print 'Error saving cache to disk - cache will not be used the next time this program runs\n{}'.format(e)

    def LoadData(self):
        try:
            json_in = open(self.__output__file, 'r')
            data = jsonpickle.decode(json_in.read())
            if data is not None:
                self.__init__(**data)
            json_in.close()
        except IOError as e:
            print 'Error reading cached file data - Clearing files and recreating cache.\n{}'.format(e)

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
