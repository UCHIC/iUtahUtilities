"""

User interface for configuring and running the HydroShare update utility

"""

import datetime
import os
import re
import smtplib
import sys
from functools import partial

__title__ = 'Visual H20 Utility'

import wx


class VisualH2O(wx.Frame):
    def __init__(self, parent, id, title):
        self.MAIN_WINDOW_SIZE = (720, 480)
        self.HydroShareConnections = []
        self.DatabaseConnections = []

        wx.Frame.__init__(self, parent, id, title, size=self.MAIN_WINDOW_SIZE)
        self.parent = parent

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

        # Combo box for selecting current/new accounts
        # Account name (label, textbox)
        # and so on...
        # Then buttons

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

    def on_edit_database(self, event):
        print "Clicked edit db button!"

    def on_database_chosen(self, event, test_arg):
        if event.GetSelection() == 1:
            print "They wanna make a new connection"
        elif event.GetSelection() > 1:
            print "They've selected a connection to use"

    def on_edit_hydroshare(self, event):
        print "Edit hydroshare clicked"

    def on_hydroshare_chosen(self, event, test_arg):
        if event.GetSelection() == 1:
            print "They wanna make a new connection"
        elif event.GetSelection() > 1:
            print "They've selected a connection to use"

    def _build_main_window(self):
        self.panel = wx.Panel(self, wx.ID_ANY)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_label_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_display_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        action_status_sizer = wx.GridBagSizer(vgap=7, hgap=7)

        edit_database_button = wx.Button(self.panel, wx.ID_EDIT)
        edit_hydroshare_button = wx.Button(self.panel, wx.ID_EDIT)
        select_database_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_databse_connections())
        select_hydroshare_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_hydroshare_accounts())

        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a database connection'), pos=(0, 0), span=(1, 4), flag=wx.ALIGN_LEFT|wx.EXPAND)
        connections_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'Select a HydroShare account'), pos=(0, 5), span=(1, 4), flag=wx.ALIGN_LEFT|wx.EXPAND)

        connections_sizer.Add(select_database_choice, pos=(1, 0), span=(1, 3), flag=wx.ALIGN_LEFT|wx.EXPAND)
        connections_sizer.Add(edit_database_button, pos=(1, 3), span=(1, 1), flag=wx.ALIGN_LEFT)
        connections_sizer.Add(select_hydroshare_choice, pos=(1, 5), span=(1, 3), flag=wx.ALIGN_LEFT|wx.EXPAND)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 8), span=(1, 1), flag=wx.ALIGN_LEFT)

        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_database, test_arg=''), edit_hydroshare_button)
        self.Bind(wx.EVT_BUTTON, partial(self.on_database_chosen, test_arg='ricket'), edit_database_button)

        self.Bind(wx.EVT_CHOICE, partial(self.on_hydroshare_chosen, test_arg="nah"), select_hydroshare_choice)

        self.Bind(wx.EVT_BUTTON, self.on_edit_database, select_database_choice)
        self.Bind(wx.EVT_BUTTON, self.on_edit_database, select_hydroshare_choice)

        main_sizer.Add(connections_sizer, wx.EXPAND|wx.ALL, 5)

        main_sizer.Add(selection_label_sizer, wx.EXPAND|wx.ALL, 5)
        main_sizer.Add(selection_display_sizer, wx.EXPAND|wx.ALL, 5)
        main_sizer.Add(action_status_sizer, wx.EXPAND|wx.ALL, 5)


        # Connection selection sizer


        # 50/50 split, 2 rows
        # Top row: Two labels
        # Bottom row, connection combo box, edit button, 50%, x2
        # buttons trigger popup window

        # H20 Selection Sizer
        # A fancy table?

        # Run and status sizer
        # 2 rows, 1 is a button the other is a progress bar


        # Logging Sizer



        # sizer = wx.GridBagSizer()
        # self.entry = wx.TextCtrl(self, -1, value=u"Enter text here.")
        # sizer.Add(self.entry, (0, 0), (1, 1), wx.EXPAND)
        # self.Bind(wx.EVT_TEXT_ENTER, self.OnPressEnter, self.entry)
        #
        # button = wx.Button(self, -1, label="Click me !")
        # sizer.Add(button, (0, 1))
        # self.Bind(wx.EVT_BUTTON, self.OnButtonClick, button)
        #
        # self.label = wx.StaticText(self, -1, label=u'Hello !')
        # self.label.SetBackgroundColour(wx.BLUE)
        # self.label.SetForegroundColour(wx.WHITE)
        # sizer.Add(self.label, (1, 0), (1, 2), wx.EXPAND)
        #
        # sizer.AddGrowableCol(0)
        #
        # self.SetSizeHints(-1, self.GetSize().y, -1, self.GetSize().y);
        #
        # self.SetSizerAndFit(sizer)
        #
        # self.CreateStatusBar()  # A Statusbar in the bottom of the window

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        # File menu
        filemenu = wx.Menu()
        filemenu.Append(wx.ID_ABOUT, "&About", " Information about this program")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")

        # Menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&File")  # Adding the "filemenu" to the MenuBar
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


if __name__ == "__main__":
    app = wx.App()
    frame = VisualH2O(None, -1, __title__)
    app.MainLoop()
