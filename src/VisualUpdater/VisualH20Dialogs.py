###########################################################################
## Class hydroshare_auth_panel
###########################################################################

import wx
import wx.xrc
from Utilities.HydroShareUtility import HydroShareAccountDetails, HydroShareUtility
from GAMUTRawData.CSVDataFileGenerator import OdmDatabaseDetails
from pubsub import pub

class HydroShareAccountDialog(wx.Dialog):
    def __init__(self, parent, accounts):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=u"HydroShare Account Details", pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE)

        pub.subscribe(self.handle_test_response, 'hs_auth_test_reply')
        self.accounts = accounts

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        dialog_sizer = wx.BoxSizer(wx.VERTICAL)

        account_selector_sizer = wx.GridBagSizer(7, 7)
        account_selector_sizer.SetFlexibleDirection(wx.BOTH)
        account_selector_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label1 = wx.StaticText(self, wx.ID_ANY, u"Modify Account", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label1.Wrap(-1)
        account_selector_sizer.Add(self.label1, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        account_selector_comboChoices = ['Add new...'] + accounts.keys()
        self.account_selector_combo = wx.Choice(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(250, -1), account_selector_comboChoices, 0)
        account_selector_sizer.Add(self.account_selector_combo, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALL | wx.EXPAND, 5)

        account_selector_sizer.AddGrowableCol(1)

        dialog_sizer.Add(account_selector_sizer, 1, wx.ALIGN_CENTER | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALIGN_RIGHT | wx.ALIGN_TOP | wx.ALL | wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP, 5)

        account_name_sizer1 = wx.GridBagSizer(7, 7)
        account_name_sizer1.SetFlexibleDirection(wx.BOTH)
        account_name_sizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label2 = wx.StaticText(self, wx.ID_ANY, u"Name", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label2.Wrap(-1)
        account_name_sizer1.Add(self.label2, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.account_name_input1 = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.account_name_input1.SetMaxLength(32)
        account_name_sizer1.Add(self.account_name_input1, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        account_name_sizer1.AddGrowableCol(1)
        dialog_sizer.Add(account_name_sizer1, 1, wx.EXPAND, 5)

        hs_username_sizer = wx.GridBagSizer(7, 7)
        hs_username_sizer.SetFlexibleDirection(wx.BOTH)
        hs_username_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label3 = wx.StaticText(self, wx.ID_ANY, u"Username", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label3.Wrap(-1)
        hs_username_sizer.Add(self.label3, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.hs_username_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.hs_username_input.SetMaxLength(32)
        hs_username_sizer.Add(self.hs_username_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        hs_username_sizer.AddGrowableCol(1)
        dialog_sizer.Add(hs_username_sizer, 1, wx.EXPAND, 5)
        hs_password_sizer = wx.GridBagSizer(7, 7)
        hs_password_sizer.SetFlexibleDirection(wx.BOTH)
        hs_password_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label4 = wx.StaticText(self, wx.ID_ANY, u"Password", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label4.Wrap(-1)
        hs_password_sizer.Add(self.label4, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.hs_password_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), wx.TE_PASSWORD)
        self.hs_password_input.SetMaxLength(32)
        hs_password_sizer.Add(self.hs_password_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        hs_password_sizer.AddGrowableCol(1)

        dialog_sizer.Add(hs_password_sizer, 1, wx.EXPAND, 5)

        client_id_sizer = wx.GridBagSizer(7, 7)
        client_id_sizer.SetFlexibleDirection(wx.BOTH)
        client_id_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label5 = wx.StaticText(self, wx.ID_ANY, u"Client ID", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label5.Wrap(-1)
        client_id_sizer.Add(self.label5, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.client_id_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.client_id_input.SetMaxLength(32)
        client_id_sizer.Add(self.client_id_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        client_id_sizer.AddGrowableCol(1)

        dialog_sizer.Add(client_id_sizer, 1, wx.EXPAND, 5)

        client_secret_sizer = wx.GridBagSizer(7, 7)
        client_secret_sizer.SetFlexibleDirection(wx.BOTH)
        client_secret_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label6 = wx.StaticText(self, wx.ID_ANY, u"Secret", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label6.Wrap(-1)
        client_secret_sizer.Add(self.label6, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.client_secret_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.client_secret_input.SetMaxLength(32)
        client_secret_sizer.Add(self.client_secret_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        client_secret_sizer.AddGrowableCol(1)

        dialog_sizer.Add(client_secret_sizer, 1, wx.EXPAND, 5)

        action_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.test_account_button = wx.Button(self, wx.ID_ANY, u"Test Account", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.test_account_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.cancel_edit_button = wx.Button(self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.cancel_edit_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.remove_account_button = wx.Button(self, wx.ID_ANY, u"Remove Account", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.remove_account_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.save_account_button = wx.Button(self, wx.ID_OK, u"Save", wx.DefaultPosition, wx.DefaultSize, 0)
        self.save_account_button.SetDefault()
        action_button_sizer.Add(self.save_account_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        dialog_sizer.Add(action_button_sizer, 1, wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP, 5)

        self.SetSizer(dialog_sizer)
        self.Layout()
        dialog_sizer.Fit(self)

        self.Centre(wx.BOTH)

        # Connect Events
        self.test_account_button.Bind(wx.EVT_BUTTON, self.on_test_account_clicked)
        self.remove_account_button.Bind(wx.EVT_BUTTON, self.on_remove_account_clicked)
        self.cancel_edit_button.Bind(wx.EVT_BUTTON, self.on_cancel_clicked)
        self.save_account_button.Bind(wx.EVT_BUTTON, self.on_save_account_clicked)
        self.account_selector_combo.Bind( wx.EVT_CHOICE, self.on_selection_changed)

    def __del__(self):
        pass

    def handle_test_response(self, reply=None):
        print reply

    def _get_input_as_dict(self):
        return dict(selector=self.account_selector_combo.GetStringSelection(),
                    name=self.account_name_input1.Value,
                    user=self.hs_username_input.Value, password=self.hs_password_input.Value,
                    client_id=self.client_id_input.Value, client_secret=self.client_secret_input.Value)

    def on_test_account_clicked(self, event):
        pub.sendMessage("hs_auth_test", result=self._get_input_as_dict())

    def on_remove_account_clicked(self, event):
        print "remove account clicked!"
        pub.sendMessage("hs_auth_remove", result=self._get_input_as_dict())

    def on_cancel_clicked(self, event):
        self.EndModal(False)

    def on_save_account_clicked(self, event):
        pub.sendMessage("hs_auth_save", result=self._get_input_as_dict())
        self.EndModal(True)

    def on_selection_changed(self, event):
        value = self.account_selector_combo.GetStringSelection()
        if value in self.accounts:
            account = self.accounts[value]
            self.account_name_input1.SetValue(account.name)
            self.hs_username_input.SetValue(account.username)
            self.hs_password_input.SetValue(account.password)
            self.client_id_input.SetValue(account.client_id if account.client_id is not None else "")
            self.client_secret_input.SetValue(account.client_secret if account.client_secret is not None else "")
        else:
            self.account_name_input1.SetValue("")
            self.hs_username_input.SetValue("")
            self.hs_password_input.SetValue("")
            self.client_id_input.SetValue("")
            self.client_secret_input.SetValue("")


class DatabaseConnectionDialog(wx.Dialog):
    def __init__(self, parent, connections):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=u'Modify Database Connections', pos=wx.DefaultPosition,
                           size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE)

        self.connections = connections

        pub.subscribe(self.handle_test_response, 'db_auth_test_reply')
        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        dialog_sizer = wx.BoxSizer(wx.VERTICAL)

        account_selector_sizer = wx.GridBagSizer(7, 7)
        account_selector_sizer.SetFlexibleDirection(wx.BOTH)
        account_selector_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label1 = wx.StaticText(self, wx.ID_ANY, u"Modify connection", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label1.Wrap(-1)
        account_selector_sizer.Add(self.label1, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        connection_selector_comboChoices = ['Add new...'] + connections.keys()
        self.connection_selector_combo = wx.Choice(self, wx.ID_ANY,  wx.DefaultPosition, wx.DefaultSize, connection_selector_comboChoices, 0)
        account_selector_sizer.Add(self.connection_selector_combo, wx.GBPosition(0, 1), wx.GBSpan(1, 2), wx.ALL | wx.EXPAND, 5)

        account_selector_sizer.AddGrowableCol(1)

        dialog_sizer.Add(account_selector_sizer, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        account_name_sizer1 = wx.GridBagSizer(7, 7)
        account_name_sizer1.SetFlexibleDirection(wx.BOTH)
        account_name_sizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label2 = wx.StaticText(self, wx.ID_ANY, u"Name", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label2.Wrap(-1)
        account_name_sizer1.Add(self.label2, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.connection_name_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.connection_name_input.SetMaxLength(32)
        account_name_sizer1.Add(self.connection_name_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1), wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        account_name_sizer1.AddGrowableCol(1)

        dialog_sizer.Add(account_name_sizer1, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        hs_username_sizer = wx.GridBagSizer(7, 7)
        hs_username_sizer.SetFlexibleDirection(wx.BOTH)
        hs_username_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label3 = wx.StaticText(self, wx.ID_ANY, u"Username", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label3.Wrap(-1)
        hs_username_sizer.Add(self.label3, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.db_username_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.db_username_input.SetMaxLength(32)
        hs_username_sizer.Add(self.db_username_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1),
                              wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        hs_username_sizer.AddGrowableCol(1)

        dialog_sizer.Add(hs_username_sizer, 1, wx.EXPAND, 5)

        hs_password_sizer = wx.GridBagSizer(7, 7)
        hs_password_sizer.SetFlexibleDirection(wx.BOTH)
        hs_password_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label4 = wx.StaticText(self, wx.ID_ANY, u"Password", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label4.Wrap(-1)
        hs_password_sizer.Add(self.label4, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.db_password_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1),
                                             wx.TE_PASSWORD)
        self.db_password_input.SetMaxLength(32)
        hs_password_sizer.Add(self.db_password_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1),
                              wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        hs_password_sizer.AddGrowableCol(1)

        dialog_sizer.Add(hs_password_sizer, 1, wx.EXPAND, 5)

        client_id_sizer = wx.GridBagSizer(7, 7)
        client_id_sizer.SetFlexibleDirection(wx.BOTH)
        client_id_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label5 = wx.StaticText(self, wx.ID_ANY, u"Hostname", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label5.Wrap(-1)
        client_id_sizer.Add(self.label5, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.hostname_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.hostname_input.SetMaxLength(32)
        client_id_sizer.Add(self.hostname_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1),
                            wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        client_id_sizer.AddGrowableCol(1)

        dialog_sizer.Add(client_id_sizer, 1, wx.EXPAND, 5)

        client_secret_sizer = wx.GridBagSizer(7, 7)
        client_secret_sizer.SetFlexibleDirection(wx.BOTH)
        client_secret_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label6 = wx.StaticText(self, wx.ID_ANY, u"Port", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label6.Wrap(-1)
        client_secret_sizer.Add(self.label6, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.port_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(65, -1), 0)
        self.port_input.SetMaxLength(32)
        client_secret_sizer.Add(self.port_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1),
                                wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        self.m_staticText28 = wx.StaticText(self, wx.ID_ANY, u"Engine", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.m_staticText28.Wrap(-1)
        client_secret_sizer.Add(self.m_staticText28, wx.GBPosition(0, 2), wx.GBSpan(1, 1), wx.ALL, 5)

        engine_selector_comboChoices = [u"mssql", u"psql"]
        self.engine_selector_combo = wx.ComboBox(self, wx.ID_ANY, u"mssql", wx.DefaultPosition, wx.Size(65, -1),
                                                 engine_selector_comboChoices, 0)
        client_secret_sizer.Add(self.engine_selector_combo, wx.GBPosition(0, 3), wx.GBSpan(1, 1), wx.ALL, 5)

        client_secret_sizer.AddGrowableCol(1)

        dialog_sizer.Add(client_secret_sizer, 1, wx.EXPAND, 5)

        databse_name_sizer = wx.GridBagSizer(7, 7)
        databse_name_sizer.SetFlexibleDirection(wx.BOTH)
        databse_name_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.label51 = wx.StaticText(self, wx.ID_ANY, u"Database name", wx.DefaultPosition, wx.Size(65, -1), 0)
        self.label51.Wrap(-1)
        databse_name_sizer.Add(self.label51, wx.GBPosition(0, 0), wx.GBSpan(1, 1), wx.ALL, 7)

        self.database_name_input = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(250, -1), 0)
        self.database_name_input.SetMaxLength(32)
        databse_name_sizer.Add(self.database_name_input, wx.GBPosition(0, 1), wx.GBSpan(1, 1),
                               wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)

        databse_name_sizer.AddGrowableCol(1)

        dialog_sizer.Add(databse_name_sizer, 1, wx.EXPAND, 5)

        action_button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.test_connection_button = wx.Button(self, wx.ID_ANY, u"Test Connection", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.test_connection_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.cancel_edit_button = wx.Button(self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.cancel_edit_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.remove_connection_button = wx.Button(self, wx.ID_ANY, u"Remove Connection", wx.DefaultPosition, wx.DefaultSize, 0)
        action_button_sizer.Add(self.remove_connection_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.save_connection_button = wx.Button(self, wx.ID_OK, u"Save Connection", wx.DefaultPosition, wx.DefaultSize, 0)
        self.save_connection_button.SetDefault()
        action_button_sizer.Add(self.save_connection_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        dialog_sizer.Add(action_button_sizer, 1, wx.LEFT | wx.RIGHT | wx.SHAPED | wx.TOP, 5)

        self.SetSizer(dialog_sizer)
        self.Layout()
        dialog_sizer.Fit(self)

        self.Centre(wx.BOTH)

        # Connect Events
        self.test_connection_button.Bind(wx.EVT_BUTTON, self.on_test_connection_clicked)
        self.cancel_edit_button.Bind(wx.EVT_BUTTON, self.on_cancel_clicked)
        self.remove_connection_button.Bind(wx.EVT_BUTTON, self.on_remove_connection_clicked)
        self.save_connection_button.Bind(wx.EVT_BUTTON, self.on_save_connection_clicked)
        self.connection_selector_combo.Bind( wx.EVT_CHOICE, self.on_selection_changed)

    def __del__(self):
        pass

    def _get_input_as_dict(self):
        return dict(selector=self.connection_selector_combo.GetStringSelection(),
                engine=self.engine_selector_combo.GetStringSelection(), user=self.db_username_input.Value,
                    password=self.db_password_input.Value, address=self.hostname_input.Value,
                    db=self.database_name_input.Value, port=self.port_input.Value,
                    name=self.connection_name_input.Value)

    def handle_test_response(self, reply=None):
        print reply

    def on_test_connection_clicked(self, event):
        print "Test connection clicked!"
        pub.sendMessage("db_auth_test", result=self._get_input_as_dict())

    def on_remove_connection_clicked(self, event):
        print "remove connection clicked!"
        pub.sendMessage("db_auth_remove", result=self._get_input_as_dict())

    def on_cancel_clicked(self, event):
        print "Cancel connection clicked!"
        self.EndModal(False)

    def on_save_connection_clicked(self, event):
        print "Save connection clicked!"
        pub.sendMessage("db_auth_save", result=self._get_input_as_dict())
        self.EndModal(True)

    def on_selection_changed(self, event):
        value = self.connection_selector_combo.GetStringSelection()
        if value in self.connections:
            connection = self.connections[value]
            self.connection_name_input.SetValue(connection.name)
            self.db_username_input.SetValue(connection.user)
            self.db_password_input.SetValue(connection.password)
            self.hostname_input.SetValue(connection.address)
            self.database_name_input.SetValue(connection.database)
            self.port_input.SetValue(connection.port)
            self.engine_selector_combo.SetSelection(1 if connection.engine == 'psql' else 0)
        else:
            self.connection_name_input.SetValue("")
            self.db_username_input.SetValue("")
            self.db_password_input.SetValue("")
            self.hostname_input.SetValue("")
            self.database_name_input.SetValue("")
            self.port_input.SetValue("")
            self.engine_selector_combo.SetSelection(0)
