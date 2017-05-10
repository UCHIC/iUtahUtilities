
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
from GAMUTRawData.CSVDataFileGenerator import OdmDatabaseDetails
from VisualH20Dialogs import HydroShareAccountDialog, DatabaseConnectionDialog

PERSIST_FILE = './persist_file'

class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        self.MAIN_WINDOW_SIZE = (720, 640)
        self.HydroShareConnections = {}
        self.DatabaseConnections = {}
        self.status_gauge = 0
        self.LoadData()

        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX,
                          size=self.MAIN_WINDOW_SIZE)
        self.parent = parent

        self.Centre()
        self._build_main_window()

        pub.subscribe(self.OnSaveHydroShareAuth, 'hs_auth_save')
        pub.subscribe(self.OnTestHydroShareAuth, 'hs_auth_test')
        pub.subscribe(self.OnRemoveHydroShareAuth, 'hs_auth_remove')
        pub.subscribe(self.OnSaveDatabaseAuth, 'db_auth_save')
        pub.subscribe(self.OnTestDatabaseAuth, 'db_auth_test')
        pub.subscribe(self.OnRemoveDatabaseAuth, 'db_auth_remove')

    def SaveData(self):
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

    def OnRemoveDatabaseAuth(self, result=None):
        if result is None:
            return
        self.DatabaseConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveDatabaseAuth(self, result=None):
        if result is None:
            return
        connection = OdmDatabaseDetails(result)
        self.DatabaseConnections.pop(result['selector'], None)
        self.DatabaseConnections[connection.name] = connection
        self.SaveData()

    def OnTestDatabaseAuth(self, result=None):
        if result is None:
            pub.sendMessage('db_auth_test_reply', reply='An error occurred, please try again later')
            return

        pub.sendMessage('db_auth_test_reply', reply='Authentication details were not accepted')
        #
        # account = HydroShareAccountDetails(result)
        # hydroshare = HydroShareUtility()
        # if hydroshare.authenticate(**account.to_dict()):
        #     pub.sendMessage('db_auth_test_reply', reply='Successfully authenticated!')
        # else:
        #     pub.sendMessage('db_auth_test_reply', reply='Authentication details were not accepted')
        # print result

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
        print "Clicked edit db button!"
        result = DatabaseConnectionDialog(self, connections).ShowModal()
        print result

    def on_edit_hydroshare(self, event, accounts=None):
        print "Edit hydroshare clicked"
        result = HydroShareAccountDialog(self, accounts).ShowModal()
        print result

    def on_database_chosen(self, event, test_arg):
        if event.GetSelection() == 1:
            print "They wanna make a new connection"
        elif event.GetSelection() > 1:
            print "They've selected a connection to use"
        else:
            print "No selection made"

    def on_hydroshare_chosen(self, event, test_arg):
        if event.GetSelection() == 1:
            print "They wanna make a new connection"
        elif event.GetSelection() > 1:
            print "They've selected a connection to use"

    def _build_main_window(self):
        ######################################
        #   Setup sizers and panels          #
        ######################################
        self.panel = wx.Panel(self, wx.ID_ANY)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_label_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_display_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        action_status_sizer = wx.GridBagSizer(vgap=7, hgap=7)

        ######################################
        #   Build connection details sizer   #
        ######################################
        edit_database_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')
        edit_hydroshare_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')

        print self._list_saved_databse_connections()

        select_database_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_databse_connections())
        select_hydroshare_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_hydroshare_accounts())
        select_database_choice.SetSelection(0)
        select_hydroshare_choice.SetSelection(0)

        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_hydroshare, accounts=self.HydroShareConnections), edit_hydroshare_button)
        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_database, connections=self.DatabaseConnections), edit_database_button)

        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a database connection'), pos=(0, 0), span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND)
        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a HydroShare account'), pos=(0, 5), span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND)

        connections_sizer.Add(edit_database_button, pos=(1, 3), span=(1, 1), flag=wx.ALIGN_LEFT)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 8), span=(1, 1), flag=wx.ALIGN_LEFT)
        connections_sizer.Add(select_hydroshare_choice, pos=(1, 5), span=(1, 3), flag=wx.ALIGN_LEFT | wx.EXPAND)
        connections_sizer.Add(select_database_choice, pos=(1, 0), span=(1, 3), flag=wx.ALIGN_LEFT | wx.EXPAND)

        ######################################
        # Build selection sizer and objects  #
        ######################################

        selection_display_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select Time Series to generate and upload'), pos=(0, 0), span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND)
        self.list_display = wx.ListCtrl(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LC_AUTOARRANGE | wx.LC_HRULES | wx.LC_REPORT | wx.LC_SORT_ASCENDING | wx.LC_VRULES)
        selection_display_sizer.Add(self.list_display, pos=(2, 0), span=(1, 4))

        ######################################
        # Build action sizer and objects     #
        ######################################

        toggle_execute_button = wx.Button(self.panel, wx.ID_ANY, label=u'Run Script')

        self.status_gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.status_gauge.SetValue(0)

        action_status_sizer.Add(toggle_execute_button, pos=(0, 8), span=(1, 1), flag=wx.ALIGN_LEFT)
        action_status_sizer.Add(self.status_gauge, pos=(0, 0), span=(1, 8), flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        main_sizer.Add(connections_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(selection_label_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(selection_display_sizer, wx.EXPAND | wx.ALL, 5)
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

    def saveConfigFile(self):
        pass

    def OnButtonClick(self, event):
        print "You clicked the button !"

    def OnPressEnter(self, event):
        print "You pressed enter !"
