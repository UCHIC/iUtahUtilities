
import datetime
import os
import re
import smtplib
import sys
from functools import partial

import wx
from VisualH20Dialogs import HydroShareAccountDialog, DatabaseConnectionDialog


class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        self.MAIN_WINDOW_SIZE = (720, 480)
        self.HydroShareConnections = []
        self.DatabaseConnections = []

        self.status_guage = 0

        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX,
                          size=self.MAIN_WINDOW_SIZE)
        self.parent = parent

        self.Centre()
        self._build_main_window()

    def _build_database_connection_interface(self):
        # 9 rows
        # 4 colums

        # Combo box for selecting current/new accounts
        # Account name (label, textbox)
        # and so on...
        # Then buttons
        pass

    def _build_hydroshare_connections_interface(self):
        # 9 rows
        # 4 colums

        pass

    def _build_resource_template_editor(self):
        # 12 rows, 8 columns
        pass

    def _list_saved_hydroshare_accounts(self):
        return ['Please select an account', 'Add HydroShare account...']

    def _list_saved_databse_connections(self):
        return ['Please select a connection', 'Add new connection...']

    def _get_hydroshare_account_by_name(self):
        pass

    def on_edit_database(self, event, test_arg=None):
        print "Clicked edit db button!"
        if test_arg == "HydroShare":
            print "Edit hydroshare clicked"
            result = HydroShareAccountDialog(self).ShowModal()
            print result
        elif test_arg == "Database":
            print "Clicked edit db button!"
            result = DatabaseConnectionDialog(self).ShowModal()
            print result
        elif test_arg is None:
            print "Got nothing"
        else:
            print test_arg

    def on_edit_hydroshare(self, event, test_arg=None):
        # print "Edit hydroshare clicked"
        # result = HydroShareAccountDialog(self).ShowModal()
        # print result
        print "Edit hydroshare clicked"
        if test_arg == "HydroShare":
            print "Edit hydroshare clicked"
            result = HydroShareAccountDialog(self).ShowModal()
            print result
        elif test_arg == "Database":
            print "Clicked edit db button!"
            result = DatabaseConnectionDialog(self).ShowModal()
            print result
        elif test_arg is None:
            print "Got nothing"
        else:
            print test_arg

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
        select_database_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_databse_connections())
        select_hydroshare_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_hydroshare_accounts())

        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_hydroshare, test_arg='HydroShare'), edit_hydroshare_button)
        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_database, test_arg='Database'), edit_database_button)

        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a database connection'), pos=(0, 0),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND)
        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a HydroShare account'), pos=(0, 5),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND)

        connections_sizer.Add(edit_database_button, pos=(1, 3), span=(1, 1), flag=wx.ALIGN_LEFT)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 8), span=(1, 1), flag=wx.ALIGN_LEFT)
        connections_sizer.Add(select_hydroshare_choice, pos=(1, 5), span=(1, 3), flag=wx.ALIGN_LEFT | wx.EXPAND)
        connections_sizer.Add(select_database_choice, pos=(1, 0), span=(1, 3), flag=wx.ALIGN_LEFT | wx.EXPAND)

        ######################################
        # Build selection sizer and objects  #
        ######################################

        ######################################
        # Build action sizer and objects     #
        ######################################

        toggle_execute_button = wx.Button(self.panel, wx.ID_ANY, label=u'Run Script')

        self.status_gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.status_gauge.SetValue(0)

        action_status_sizer.Add(toggle_execute_button, pos=(3, 8), span=(1, 1), flag=wx.ALIGN_LEFT)
        action_status_sizer.Add(self.status_gauge, pos=(3, 0), span=(1, 8), flag=
                              wx.ALIGN_CENTER | wx.ALL | wx.EXPAND)

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

        # self.panel.SetSizeHints(720, 480, 1028, 960)
        self.panel.SetSizerAndFit(main_sizer)
        self.Show(True)

    def saveConfigFile(self):
        pass

    def OnButtonClick(self, event):
        print "You clicked the button !"

    def OnPressEnter(self, event):
        print "You pressed enter !"
