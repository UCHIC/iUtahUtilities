
import datetime
import os
import re
import smtplib
import sys
from functools import partial

import wx
import jsonpickle
# import wx.lib.pubsub.pub as Publisher
from pubsub import pub
from Utilities.HydroShareUtility import HydroShareAccountDetails, HydroShareUtility
from Utilities.Odm2Wrapper import *
from GAMUTRawData.CSVDataFileGenerator import OdmDatabaseDetails
from GAMUTRawData.odmservices import ServiceManager
from EditConnectionsDialog import DatabaseConnectionDialog
from EditAccountsDialog import HydroShareAccountDialog
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog


PERSIST_FILE = './persist_file'
service_manager = ServiceManager()

class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        ###########################################
        # Declare/populate variables, wx objects  #
        ###########################################
        self.MAIN_WINDOW_SIZE = (720, 640)
        self.HydroShareConnections = {}
        self.DatabaseConnections = {}

        self.ActiveOdmConnection = None  # type: ServiceManager
        self.ActiveHydroshare = None     # type: HydroShareUtility

        # Load persistence file
        try:
            self.LoadData()
        except:
            print "This looks like a first run"

        # Widgets
        self.status_gauge = None              # type: wx.Gauge
        self.select_database_choice = None    # type: wx.Choice
        self.select_hydroshare_choice = None  # type: wx.Choice
        self.odm2_series_display = None       # type: wx.ListCtrl
        # self.hydroshare_display = None        # type: # wx.ListCtrl
        self.hydroshare_display = None        # type: wx.ListBox

        # just technicalities, honestly
        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, size=self.MAIN_WINDOW_SIZE)
        self.parent = parent
        self.Centre()
        self._build_main_window()

        ###########################################
        # Setup subscribers/publishers callbacks  #
        ###########################################
        pub.subscribe(self.OnSaveHydroShareAuth, 'hs_auth_save')
        pub.subscribe(self.OnTestHydroShareAuth, 'hs_auth_test')
        pub.subscribe(self.OnRemoveHydroShareAuth, 'hs_auth_remove')
        pub.subscribe(self.OnSaveDatabaseAuth, 'db_auth_save')
        pub.subscribe(self.OnTestDatabaseAuth, 'db_auth_test')
        pub.subscribe(self.OnRemoveDatabaseAuth, 'db_auth_remove')

    def SaveData(self):
        self.UpdateControls()
        data = {'HS': self.HydroShareConnections, 'DB': self.DatabaseConnections}
        try:
            json_out = open(PERSIST_FILE, 'w')
            json_out.write(jsonpickle.encode(data))
            json_out.close()
        except IOError as e:
            print 'Error saving cache to disk - cache will not be used the next time this program runs\n{}'.format(e)

    def LoadData(self):
        try:
            json_in = open(PERSIST_FILE, 'r')
            data = jsonpickle.decode(json_in.read())
            self.HydroShareConnections = data['HS'] if 'HS' in data else {}
            self.DatabaseConnections = data['DB'] if 'DB' in data else {}
            json_in.close()
        except IOError as e:
            print 'Error reading cached file data - Clearing files and recreating cache.\n{}'.format(e)

    def UpdateControls(self, progress=None):
        if progress is not None:
            self.status_gauge = progress if 100 >= progress >= 0 else progress % 100

        if self.select_database_choice is not None:
            db_selected = self.select_database_choice.GetCurrentSelection()
            self.select_database_choice.Clear()
            self.select_database_choice.SetItems(self._list_saved_databse_connections())
            self.select_database_choice.SetSelection(db_selected)

        if self.select_hydroshare_choice is not None:
            hs_selected = self.select_hydroshare_choice.GetCurrentSelection()
            self.select_hydroshare_choice.Clear()
            self.select_hydroshare_choice.SetItems(self._list_saved_hydroshare_accounts())
            self.select_hydroshare_choice.SetSelection(hs_selected)

        if self.odm2_series_display is not None:
            pass

        if self.hydroshare_display is not None:
            pass


    def OnRemoveDatabaseAuth(self, result=None):
        if result is None:
            return
        self.DatabaseConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveDatabaseAuth(self, result=None):
        if result is None:
            return
        connection = OdmDatabaseDetails(result)
        self.DatabaseConnections.pop(result['name'], None)
        self.DatabaseConnections[connection.name] = connection
        self.SaveData()

    def OnTestDatabaseAuth(self, result=None):
        if result is None:
            pub.sendMessage('db_auth_test_reply', reply='An error occurred, please try again later')
            return
        db_details = OdmDatabaseDetails(result)
        if db_details.VerifyConnection():
            pub.sendMessage('db_auth_test_reply', reply='Successfully authenticated!')
        else:
            pub.sendMessage('db_auth_test_reply', reply='Authentication details were not accepted')

    def OnRemoveHydroShareAuth(self, result=None):
        if result is None:
            return
        self.HydroShareConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveHydroShareAuth(self, result=None):
        if result is None:
            return
        account = HydroShareAccountDetails(result)
        self.HydroShareConnections.pop(result['selector'], None)
        self.HydroShareConnections[account.name] = account
        self.SaveData()

    def OnTestHydroShareAuth(self, result=None):
        if result is None:
            pub.sendMessage('hs_auth_test_reply', reply='An error occurred, please try again later')
            return

        account = HydroShareAccountDetails(result)
        hydroshare = HydroShareUtility()
        if hydroshare.authenticate(**account.to_dict()):
            pub.sendMessage('hs_auth_test_reply', reply='Successfully authenticated!')
        else:
            pub.sendMessage('hs_auth_test_reply', reply='Authentication details were not accepted')
        print result

    def _list_saved_hydroshare_accounts(self):
        if len(self.HydroShareConnections) > 0:
            return ['Select an account'] + [account for account in self.HydroShareConnections.keys()]
        else:
            return ['No saved accounts']

    def _list_saved_databse_connections(self):
        if len(self.DatabaseConnections) > 0:
            return ['Select a connection'] + [connection for connection in self.DatabaseConnections.keys()]
        else:
            return ['No saved connections']

    def _get_hydroshare_account_by_name(self):
        pass

    def on_edit_database(self, event, connections=None):
        result = DatabaseConnectionDialog(self, connections, self.select_database_choice.GetCurrentSelection()).ShowModal()
        print result
        event.Skip()

    def on_edit_hydroshare(self, event, accounts=None):
        result = HydroShareAccountDialog(self, accounts, self.select_hydroshare_choice.GetCurrentSelection()).ShowModal()
        print result
        event.Skip()

    def on_database_chosen(self, event):
        if event.GetSelection() > 0:
            print "Lets connect"
            selection_string = self.select_database_choice.GetStringSelection()
            print selection_string
            connection = self.DatabaseConnections[selection_string]
            if connection.VerifyConnection():
                service_manager._current_connection = connection.ToDict()
                series_service = service_manager.get_series_service()
                series_list = series_service.get_all_series()
                for series in series_list:
                    print series
                    self.odm2_series_display.Append(str(series))
        else:
            print "No selection made"
        event.Skip()

    def on_hydroshare_chosen(self, event):
        if event.GetSelection() == 0:
            print "No selection was made"

        account_string = self.select_hydroshare_choice.GetStringSelection()
        account_details = self.HydroShareConnections[account_string]  # type: HydroShareAccountDetails
        self.ActiveHydroshare = HydroShareUtility()
        if self.ActiveHydroshare.authenticate(**account_details.to_dict()):
            print 'successful auth to hydroshare'
            resources = self.ActiveHydroshare.filterOwnedResourcesByRegex('.*')
            for resource in resources:
                print resource
                self.hydroshare_display.Append(str(resource))
        event.Skip()

    def OnClick(self, event):
        print 'Clicked!!'
        event.Skip()

    def _build_main_window(self):
        ######################################
        #   Setup sizers and panels          #
        ######################################
        self.panel = wx.Panel(self, wx.ID_ANY)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_label_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        data_management_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_status_sizer = wx.GridBagSizer(vgap=7, hgap=7)

        ######################################
        #   Build connection details sizer   #
        ######################################
        edit_database_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')
        edit_hydroshare_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')

        self.select_database_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_databse_connections())
        self.select_hydroshare_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_hydroshare_accounts())
        self.select_database_choice.SetMinSize(wx.Size(225, -1))
        self.select_database_choice.SetMaxSize(wx.Size(225, -1))
        self.select_hydroshare_choice.SetMinSize(wx.Size(225,-1))
        self.select_hydroshare_choice.SetMaxSize(wx.Size(225,-1))
        self.select_database_choice.SetSelection(0)
        self.select_hydroshare_choice.SetSelection(0)

        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_hydroshare, accounts=self.HydroShareConnections), edit_hydroshare_button)
        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_database, connections=self.DatabaseConnections), edit_database_button)
        self.Bind(wx.EVT_CHOICE, self.on_hydroshare_chosen, self.select_hydroshare_choice)
        self.Bind(wx.EVT_CHOICE, self.on_database_chosen, self.select_database_choice)

        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a database connection'), pos=(0, 0), span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.TOP | wx.EXPAND | wx.EXPAND, border=7)
        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a HydroShare account'), pos=(0, 5), span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.TOP | wx.EXPAND | wx.EXPAND, border=7)

        connections_sizer.Add(edit_database_button, pos=(1, 3), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.EXPAND, border=7)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 8), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.RIGHT | wx.EXPAND, border=7)
        connections_sizer.Add(self.select_hydroshare_choice, pos=(1, 5), span=(1, 3), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND, border=7)
        connections_sizer.Add(self.select_database_choice, pos=(1, 0), span=(1, 3), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND, border=7)

        ######################################
        # Build selection sizer and objects  #
        ######################################

        self.odm2_series_display = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [], wx.LC_ALIGN_LEFT | wx.LC_ALIGN_TOP | wx.LC_HRULES | wx.LC_REPORT | wx.LC_SORT_ASCENDING)
        self.odm2_series_display.SetMinSize(wx.Size(300, -1))
        self.odm2_series_display.SetMaxSize(wx.Size(300, -1))
        self.hydroshare_display = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [], wx.LC_ALIGN_LEFT | wx.LC_ALIGN_TOP | wx.LC_HRULES | wx.LC_REPORT | wx.LC_SORT_ASCENDING)
        self.hydroshare_display.SetMinSize(wx.Size(300, -1))
        self.hydroshare_display.SetMaxSize(wx.Size(300, -1))

        self.Bind(wx.EVT_LISTBOX, self.OnClick, self.hydroshare_display)

        data_management_sizer.SetMinSize(wx.Size(635, -1))
        data_management_sizer.Add(self.odm2_series_display, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        data_management_sizer.Add(self.hydroshare_display, 0, wx.ALL, 5)

        ######################################
        # Build action sizer and objects     #
        ######################################

        toggle_execute_button = wx.Button(self.panel, wx.ID_ANY, label=u'Run Script')

        self.status_gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.status_gauge.SetValue(0)

        action_status_sizer.Add(toggle_execute_button, pos=(0, 8), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, border=7)
        action_status_sizer.Add(self.status_gauge, pos=(0, 0), span=(1, 8), flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, border=7)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        main_sizer.Add(connections_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(selection_label_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(data_management_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(action_status_sizer, wx.EXPAND | wx.ALL, 5)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_ABOUT, "&About", " Information about this program")
        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_CLOSE, 'Quit', 'Quit application')

        # Menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")  # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        self.panel.SetSizerAndFit(main_sizer)
        self.Show(True)

    def OnButtonClick(self, event):
        print "You clicked the button !"
        event.Skip()


    def OnPressEnter(self, event):
        print "You pressed enter !"
        event.Skip()
