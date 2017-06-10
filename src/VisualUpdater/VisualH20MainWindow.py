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
from Utilities.DatasetGenerator import OdmDatasetUtility
from Utilities.ActionManager import *
from Utilities.Odm2Wrapper import *
from GAMUTRawData.odmservices import ServiceManager
from EditConnectionsDialog import DatabaseConnectionDialog
from EditAccountsDialog import HydroShareAccountDialog
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog
from H20MapWidget import H20MapWidget
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog
from InputValidator import *

service_manager = ServiceManager()

RE_SERIES_INFO = re.compile(r'^(?P<id>\d+) +(?P<site>\S+) +(?P<var>\S+) +QC (?P<qc>[\d.]+)$', re.I)

# transformer = {
#    "Buzzstream Field #2": lambda our_field: our_field * 2,
#     "Buzzstream #3": lambda num2: return num2/2
# }
#
# for field in buzz_fields:
#     if field in transformer:
#         buzz_field = transformer[field](out_field)
#
# def dothing(stuff):
#     print(stuff)
#
# switcheroo = {
#     1: lambda thing: dothing(thing),
#     2: dothing
# }
#
# switcheroo[1]()
#
# def add(a, b):
#     return a+b
#
# def add7(a):
#     return add(7, a)
#

series_to_string = lambda series: (str(series.id).ljust(6) + series.site_code.ljust(20) +
                                   series.variable_code.ljust(20) + ' QC {}'.format(series.quality_control_level_code))


class Orientation:
    VERTICAL = 1
    HORIZONTAL = 0


class WxHelper:
    # def __init__(self, app, panel):


    @staticmethod
    def GetBitmap(path, size_x=None, size_y=None):
        image = wx.Bitmap.ConvertToImage(wx.Bitmap(path, wx.BITMAP_TYPE_ANY))
        if size_x is not None and size_y is not None:
            image = image.Scale(size_x, size_y, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    @staticmethod
    def InitializeGridBagSizer(padding_x=5, padding_y=5):
        sizer = wx.GridBagSizer(vgap=padding_y, hgap=padding_x)
        sizer.SetFlexibleDirection(direction=wx.BOTH)
        sizer.SetNonFlexibleGrowMode(mode=wx.FLEX_GROWMODE_ALL)
        return sizer

    @staticmethod
    def InitializeRadioBox(parent, label, options, orientation=Orientation.VERTICAL):
        radiobox = wx.RadioBox(parent, wx.ID_ANY, label, wx.DefaultPosition, wx.DefaultSize, options, orientation,
                               wx.RA_SPECIFY_ROWS)
        radiobox.SetSelection(0)
        return radiobox

    @staticmethod
    def InitializeButton(app, parent, label, event_function=None, size_x=None, size_y=None):
        button = wx.Button(parent, wx.ID_ANY, label, wx.DefaultPosition, wx.DefaultSize, 0)
        if size_x is not None and size_y is not None:
            button.SetMinSize(wx.Size(size_x, size_y))
            button.SetMaxSize(wx.Size(size_x, size_y))
        if event_function is not None:
            app.Bind(wx.EVT_BUTTON, event_function, button)
        return button

    @staticmethod
    def GetLabel(parent, text):
        return wx.StaticText(parent, wx.ID_ANY, text)


class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        ###########################################
        # Declare/populate variables, wx objects  #
        ###########################################
        self.MAIN_WINDOW_SIZE = (940, 860)
        self.WX_MONOSPACE = wx.Font(9, 75, 90, 90, False, "Inconsolata")
        self.ActionManager = ActionManager()
        self.ActionManager.__output__file = PERSIST_OP_FILE

        self.ActiveOdmConnection = None  # type: ServiceManager
        self.ActiveHydroshare = None  # type: HydroShareUtility

        self._series_dict = {}  # type: dict[int, Series]
        self._resources = None  # type: list[HydroShareResource]

        try:
            self.LoadData()
        except:
            print "This looks like a first run"

        # Widgets
        self.status_gauge = None  # type: wx.Gauge
        self.select_database_choice = None  # type: wx.Choice
        self.select_hydroshare_choice = None  # type: wx.Choice
        self.mapping_grid = None  # type: H20Widget
        self.dataset_prefix_input = None  # type: wx.TextCtrl
        self.available_series_listbox = None  # type: wx.ListBox

        # just technicalities, honestly
        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX,
                          size=self.MAIN_WINDOW_SIZE)
        self.parent = parent
        self.Centre()
        self._build_main_window()

        ###########################################
        # Setup subscribers/publishers callbacks  #
        ###########################################
        pub.subscribe(self.OnDeleteResourceTemplate, 'hs_resource_remove')
        pub.subscribe(self.OnSaveResourceTemplate, 'hs_resource_save')
        pub.subscribe(self.OnSaveHydroShareAuth, 'hs_auth_save')
        pub.subscribe(self.OnTestHydroShareAuth, 'hs_auth_test')
        pub.subscribe(self.OnRemoveHydroShareAuth, 'hs_auth_remove')
        pub.subscribe(self.OnSaveDatabaseAuth, 'db_auth_save')
        pub.subscribe(self.OnTestDatabaseAuth, 'db_auth_test')
        pub.subscribe(self.OnRemoveDatabaseAuth, 'db_auth_remove')
        pub.subscribe(self.OnPrintLog, 'logger')

    def OnPrintLog(self, message=""):
        if message is None or not isinstance(message, str) or len(message) == 0:
            return
        self.log_message_listbox.Append(message)

    def SaveData(self):
        self.UpdateControls()
        self.ActionManager.SaveData()

    def LoadData(self):
        self.ActionManager.LoadData()

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

    def OnDeleteResourceTemplate(self, result=None):
        if result is None:
            return
        self.ActionManager.ResourceTemplates.pop(result['selector'], None)
        self.SaveData()

    def OnSaveResourceTemplate(self, result=None):
        if result is None:
            return
        template = ResourceTemplate(result)
        self.ActionManager.ResourceTemplates.pop(result['selector'], None)
        self.ActionManager.ResourceTemplates[template.template_name] = template
        self.SaveData()

    def OnRemoveDatabaseAuth(self, result=None):
        if result is None:
            return
        self.ActionManager.DatabaseConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveDatabaseAuth(self, result=None):
        if result is None:
            return
        connection = OdmDatasetUtility(result)
        self.ActionManager.DatabaseConnections.pop(result['selector'], None)
        self.ActionManager.DatabaseConnections[connection.name] = connection
        self.SaveData()

    def OnTestDatabaseAuth(self, result=None):
        if result is None:
            pub.sendMessage('db_auth_test_reply', reply='An error occurred, please try again later')
            return
        db_details = OdmDatasetUtility(result)
        if db_details.VerifyConnection():
            pub.sendMessage('db_auth_test_reply', reply='Successfully authenticated!')
        else:
            pub.sendMessage('db_auth_test_reply', reply='Authentication details were not accepted')

    def OnRemoveHydroShareAuth(self, result=None):
        if result is None:
            return
        self.ActionManager.HydroShareConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveHydroShareAuth(self, result=None):
        if result is None:
            return
        account = HydroShareAccountDetails(result)
        self.ActionManager.HydroShareConnections.pop(result['selector'], None)
        self.ActionManager.HydroShareConnections[account.name] = account
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
        if len(self.ActionManager.HydroShareConnections) > 0:
            return ['Select an account'] + [account for account in self.ActionManager.HydroShareConnections.keys()]
        else:
            return ['No saved accounts']

    def _list_saved_databse_connections(self):
        if len(self.ActionManager.DatabaseConnections) > 0:
            return ['Select a connection'] + [connection for connection in
                                              self.ActionManager.DatabaseConnections.keys()]
        else:
            return ['No saved connections']

    def _get_hydroshare_account_by_name(self):
        pass

    def on_edit_database(self, event, connections=None):
        result = DatabaseConnectionDialog(self, self.ActionManager.DatabaseConnections,
                                          self.select_database_choice.GetCurrentSelection()).ShowModal()

    def on_edit_hydroshare(self, event, accounts=None):
        result = HydroShareAccountDialog(self, self.ActionManager.HydroShareConnections,
                                         self.select_hydroshare_choice.GetCurrentSelection()).ShowModal()

    def on_database_chosen(self, event):
        self.available_series_listbox.Clear()
        self.selected_series_listbox.Clear()
        self.OnPrintLog('Database selected - fetching series')
        if event.GetSelection() > 0:
            self._series_dict.clear()
            selection_string = self.select_database_choice.GetStringSelection()
            connection = self.ActionManager.DatabaseConnections[selection_string]
            if connection.VerifyConnection():
                service_manager._current_connection = connection.ToDict()
                series_service = service_manager.get_series_service()
                series_list = series_service.get_all_series()
                for series in series_list:
                    self._series_dict[series.id] = series
                self.UpdateSeriesInGrid()
        else:
            print "No selection made"
        event.Skip()

    def on_hydroshare_chosen(self, event):
        self._resources = None
        if event.GetSelection() != 0:
            account_string = self.select_hydroshare_choice.GetStringSelection()
            account_details = self.ActionManager.HydroShareConnections[account_string]  # type: HydroShareAccountDetails
            self.ActiveHydroshare = HydroShareUtility()
            if self.ActiveHydroshare.authenticate(**account_details.to_dict()):
                self._resources = self.ActiveHydroshare.getAllResources()
                self.OnPrintLog('Successfully authenticated HydroShare account details')
            else:
                self.OnPrintLog('Unable to authenticate HydroShare account - please check your credentials')
        self._update_target_choices()
        event.Skip()

    def SeriesToString(self, series):
        num = str(series.id).ljust(6)
        site = series.site_code.ljust(20)
        var = series.variable_code.ljust(20)
        qc = ' QC {}'.format(series.quality_control_level_code)
        return '{} {} {} {}'.format(num, site, var, qc)

    def UpdateSeriesInGrid(self, event=None):
        if self._series_dict is None:
            self.selected_series_listbox.SetItems(['No Selected Series'])
            self.selected_series_listbox.SetItems(['No Available Series'])
            self.remove_from_selected_button.Disable()
            self.add_to_selected_button.Disable()
            return

        self.available_series_listbox.Clear()
        for series in self._series_dict.values():
            self.available_series_listbox.Append(series_to_string(series))

        self.remove_from_selected_button.Enable()
        self.add_to_selected_button.Enable()

    def _build_category_context_menu(self, selected_item, evt_parent):
        series_category_menu = wx.Menu()
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"Site: Select All", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"Site: Deselect All", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"Variable: Select All", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"Variable: Deselect All", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"QC Code: Select All", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.Append(
            wx.MenuItem(series_category_menu, wx.ID_ANY, u"QC Code: Deselect All", wx.EmptyString, wx.ITEM_NORMAL))

        if evt_parent == 'Selected Listbox':
            listbox = self.selected_series_listbox
        else:
            listbox = self.available_series_listbox

        for item in series_category_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, partial(self._category_selection, control=listbox, direction=item.GetText(),
                                           curr_index=selected_item), item)
        return series_category_menu

    def _move_to_selected_series(self, event):
        if len(self.selected_series_listbox.Items) == 1 and self.selected_series_listbox.GetString(
                0) == 'No Selected Series':
            self.selected_series_listbox.Delete(0)

        selected = [self.available_series_listbox.GetString(i) for i in self.available_series_listbox.GetSelections()]
        for item in selected:
            self.selected_series_listbox.Append(item)
            self.available_series_listbox.Delete(self.available_series_listbox.FindString(item))

        if len(self.available_series_listbox.Items) == 0:
            self.available_series_listbox.Append('No Available Series')

    def _move_from_selected_series(self, event):
        if len(self.available_series_listbox.Items) == 1 and self.available_series_listbox.GetString(
                0) == 'No Available Series':
            self.available_series_listbox.Delete(0)

        selected = [self.selected_series_listbox.GetString(i) for i in self.selected_series_listbox.GetSelections()]
        for item in selected:
            self.available_series_listbox.Insert(item, 0)
            self.selected_series_listbox.Delete(self.selected_series_listbox.FindString(item))

        if len(self.selected_series_listbox.Items) == 0:
            self.selected_series_listbox.Append('No Selected Series')

    def OnAvailableCategoryRightClick(self, event):
        evt_pos = event.GetPosition()
        list_pos = self.available_series_listbox.ScreenToClient(evt_pos)
        item_int = self.available_series_listbox.HitTest(list_pos)
        if item_int >= 0:
            self.PopupMenu(self._build_category_context_menu(item_int, 'Available Listbox'))

    def OnSelectedCategoryRightClick(self, event):
        evt_pos = event.GetPosition()
        list_pos = self.selected_series_listbox.ScreenToClient(evt_pos)
        item_int = self.selected_series_listbox.HitTest(list_pos)
        if item_int >= 0:
            self.PopupMenu(self._build_category_context_menu(item_int, 'Selected Listbox'))

    def _category_selection(self, event, direction, control, curr_index):
        category, action = direction.split(u': ')
        check_series = self._series_dict[int(RE_SERIES_INFO.match(control.Items[curr_index]).groupdict()['id'])]

        for ctrl_index in range(0, len(control.Items)):
            series_dict = RE_SERIES_INFO.match(control.Items[ctrl_index]).groupdict()
            site_modify = category == 'Site' and series_dict['site'] == check_series.site_code
            var_modify = category == 'Variable' and series_dict['var'] == check_series.variable_code
            qc_modify = category == 'QC Code' and series_dict['qc'] == check_series.quality_control_level_code
            if site_modify or var_modify or qc_modify:
                if action == 'Select All':
                    control.Select(ctrl_index)
                elif action == 'Deselect All':
                    control.Deselect(ctrl_index)

    def _update_target_choices(self, event=None):
        if self._resources is None and self.hydroshare_destination_radio.GetSelection() == 1:
            self.select_destination_choice.SetItems(['Please connect to a HydroShare account'])
            self.select_destination_choice.SetSelection(0)
            return

        if self.hydroshare_destination_radio.GetSelection() == 1:
            self.select_destination_choice.SetItems([item.title for item in self._resources])
        else:
            self.select_destination_choice.SetItems([str(item) for item in self.ActionManager.ResourceTemplates])

        self.select_destination_choice.SetSelection(0)

        if event is not None:
            event.Skip()

    def _save_dataset_clicked(self, event):
        if len(self.selected_series_listbox.Items) == 0:
            self.OnPrintLog('Invalid options - please select the ODM series you would like to add to the dataset')
            return
        if len(self.selected_series_listbox.Items) == 1 and self.selected_series_listbox.GetString(
                0) == 'No Selected Series':
            self.OnPrintLog('Invalid options - please select the ODM series you would like to add to the dataset')
            return
        if self.select_hydroshare_choice.GetSelection() == 0:
            self.OnPrintLog('Invalid options - please select a HydroShare account to use')
            return
        if self.hydroshare_destination_radio.GetSelection() == '1' and self.select_destination_choice.GetSelection() == 0:
            self.OnPrintLog('Invalid options - please select a destination HydroShare resource')
            return

        string_result = 'Marked {} series for upload to {}'.format(len(self.selected_series_listbox.Items),
                                                                   self.select_destination_choice.GetStringSelection())
        self.log_message_listbox.Append(string_result)
        curr_dataset = H2ODataset(
            name=self.dataset_name_input.Value,
            odm_series=[int(RE_SERIES_INFO.match(item).groupdict()['id']) for item in
                        self.selected_series_listbox.Items],
            hs_resource=self.select_hydroshare_choice.GetStringSelection(),
            odm_db_name=self.select_database_choice.GetStringSelection(),
            chunk_by_series=self.grouping_radio_buttons.GetSelection() == 1,
            chunk_by_year=self.chunk_checkbox.Value
        )

    def _build_main_window(self):
        ######################################
        #   Setup sizers and panels          #
        ######################################
        self.panel = wx.Panel(self, wx.ID_ANY)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = WxHelper.InitializeGridBagSizer()
        selection_label_sizer = WxHelper.InitializeGridBagSizer()
        dataset_resource_sizer = WxHelper.InitializeGridBagSizer()
        action_status_sizer = WxHelper.InitializeGridBagSizer()

        ######################################
        #   Build connection details sizer   #
        ######################################
        edit_database_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')
        edit_hydroshare_button = wx.Button(self.panel, wx.ID_ANY, label=u'Edit...')

        self.select_database_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_databse_connections())
        self.select_hydroshare_choice = wx.Choice(self.panel, wx.ID_ANY, choices=self._list_saved_hydroshare_accounts())
        self.select_database_choice.SetMinSize(wx.Size(260, 23))
        self.select_hydroshare_choice.SetMinSize(wx.Size(260, 23))
        self.select_database_choice.SetSelection(0)
        self.select_hydroshare_choice.SetSelection(0)

        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_hydroshare, accounts=self.ActionManager.HydroShareConnections),
                  edit_hydroshare_button)
        self.Bind(wx.EVT_BUTTON, partial(self.on_edit_database, connections=self.ActionManager.DatabaseConnections),
                  edit_database_button)
        self.Bind(wx.EVT_CHOICE, self.on_hydroshare_chosen, self.select_hydroshare_choice)
        self.Bind(wx.EVT_CHOICE, self.on_database_chosen, self.select_database_choice)

        connections_sizer.Add(self.GetLabel(u'Select a database connection'), pos=(0, 0),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.EXPAND | wx.RIGHT, border=7)
        connections_sizer.Add(self.select_database_choice, pos=(1, 0), span=(1, 4),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=7)
        connections_sizer.Add(edit_database_button, pos=(1, 4), span=(1, 1),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT, border=7)

        connections_sizer.Add(self.GetLabel(u'Select a HydroShare account'), pos=(0, 8),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.EXPAND | wx.RIGHT, border=15)
        connections_sizer.Add(self.select_hydroshare_choice, pos=(1, 8), span=(1, 4),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=15)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 12), span=(1, 1),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT, border=15)

        ######################################
        # Build selection sizer and objects  #
        ######################################

        self.available_series_listbox = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                                   ['No Available Series'], wx.LB_EXTENDED)
        self.available_series_listbox.SetMinSize(wx.Size(375, 200))
        self.available_series_listbox.SetFont(self.WX_MONOSPACE)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnAvailableCategoryRightClick, self.available_series_listbox)

        self.selected_series_listbox = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                                  ['No Selected Series'], wx.LB_EXTENDED)
        self.selected_series_listbox.SetMinSize(wx.Size(375, 200))
        self.selected_series_listbox.SetFont(self.WX_MONOSPACE)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnSelectedCategoryRightClick, self.selected_series_listbox)

        self.grouping_radio_buttons = WxHelper.InitializeRadioBox(self.panel, u"Series File Grouping",
                                                                  [u"Single File for all series",
                                                                   u"One file per series"])

        self.chunk_checkbox = wx.CheckBox(self.panel, wx.ID_ANY, u"Chunk file(s) by year", wx.Point(-1, -1),
                                          wx.DefaultSize, 0)

        self.hydroshare_destination_radio = WxHelper.InitializeRadioBox(self.panel, u"HydroShare Resource",
                                                                        [u"Create new resource from template",
                                                                         u"Use an existing HydroShare resource"])
        self.hydroshare_destination_radio.SetSelection(1)
        self.Bind(wx.EVT_RADIOBOX, self._update_target_choices, self.hydroshare_destination_radio)

        self.select_destination_choice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                                   ['Please connect to a HydroShare account'], 0)
        self.select_destination_choice.SetMaxSize(wx.Size(-1, 25))
        self.select_destination_choice.SetSelection(0)

        # Buttons (and bitmaps) to add or remove series from the active dataset
        left_arrow = WxHelper.GetBitmap('./VisualUpdater/previous_icon.png', 20, 20)
        right_arrow = WxHelper.GetBitmap('./VisualUpdater/next_icon.png', 20, 20)

        self.add_to_selected_button = wx.BitmapButton(self.panel, wx.ID_ANY, right_arrow, wx.DefaultPosition,
                                                      wx.DefaultSize)
        self.Bind(wx.EVT_BUTTON, self._move_to_selected_series, self.add_to_selected_button)

        self.remove_from_selected_button = wx.BitmapButton(self.panel, wx.ID_ANY, left_arrow, wx.DefaultPosition,
                                                           wx.DefaultSize)
        self.Bind(wx.EVT_BUTTON, self._move_from_selected_series, self.remove_from_selected_button)

        self.remove_from_selected_button.Disable()
        self.add_to_selected_button.Disable()

        # Dataset action buttons
        self.save_dataset_button = WxHelper.InitializeButton(self, self.panel, u" Save Dataset ",
                                                             self._save_dataset_clicked, 100, 30)
        self.copy_dataset_button = WxHelper.InitializeButton(self, self.panel, u" Copy Dataset ",
                                                             self._save_dataset_clicked, 100, 30)
        self.delete_dataset_button = WxHelper.InitializeButton(self, self.panel, u"Delete Dataset",
                                                               self._save_dataset_clicked, 100, 30)

        # Dataset choice and input
        self.dataset_selector_choice = wx.Choice(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                                 ['Create new dataset'], 1)
        self.dataset_selector_choice.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnDatasetChoiceModified, self.dataset_selector_choice)

        self.dataset_name_input = wx.TextCtrl(self.panel, wx.ID_ANY, u'', wx.DefaultPosition, wx.DefaultSize, 7,
                                              validator=CharValidator(PATTERNS.CV_WORD))
        self.dataset_name_input.SetMinSize(wx.Size(275, 25))

        ###################################################
        # Most things, but with the options all on left   #
        ###################################################

        dataset_resource_sizer.Add(self.GetLabel(u'Available Series'), pos=(4, 0), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=5)
        dataset_resource_sizer.Add(self.GetLabel(u'Selected Series'), pos=(4, 5), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=5)
        dataset_resource_sizer.Add(self.available_series_listbox, pos=(5, 0), span=(6, 4),
                                   flag=wx.ALIGN_CENTER | wx.LEFT | wx.EXPAND, border=7)
        dataset_resource_sizer.Add(self.selected_series_listbox, pos=(5, 5), span=(6, 4),
                                   flag=wx.ALIGN_CENTER | wx.RIGHT | wx.EXPAND, border=7)
        dataset_resource_sizer.Add(self.add_to_selected_button, pos=(7, 4), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=2)
        dataset_resource_sizer.Add(self.remove_from_selected_button, pos=(8, 4), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, border=2)

        dataset_resource_sizer.Add(self.GetLabel(u'Datasets'), pos=(0, 0), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.TOP, border=7)
        dataset_resource_sizer.Add(self.dataset_selector_choice, pos=(1, 0), span=(1, 4),
                                   flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=7)
        dataset_resource_sizer.Add(self.GetLabel(u'Name'), pos=(0, 5), span=(1, 1),
                                   flag=wx.ALIGN_CENTER | wx.RIGHT | wx.EXPAND | wx.TOP, border=7)
        dataset_resource_sizer.Add(self.dataset_name_input, pos=(1, 5), span=(1, 4),
                                   flag=wx.ALIGN_LEFT | wx.EXPAND | wx.RIGHT, border=7)

        dataset_resource_sizer.Add(self.hydroshare_destination_radio, pos=(2, 0), span=(1, 4),
                                   flag=wx.ALIGN_LEFT | wx.ALL, border=5)
        dataset_resource_sizer.Add(self.select_destination_choice, pos=(3, 0), span=(1, 4),
                                   flag=wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, border=5)

        dataset_resource_sizer.Add(self.grouping_radio_buttons, pos=(2, 5), span=(1, 3), flag=wx.ALIGN_LEFT | wx.ALL,
                                   border=7)
        dataset_resource_sizer.Add(self.chunk_checkbox, pos=(2, 8), span=(1, 1), flag=wx.ALIGN_CENTER | wx.RIGHT,
                                   border=7)

        dataset_resource_sizer.Add(self.delete_dataset_button, pos=(3, 8), span=(1, 1), flag=wx.ALIGN_LEFT | wx.ALL,
                                   border=2)
        dataset_resource_sizer.Add(self.copy_dataset_button, pos=(3, 7), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                                   border=2)
        dataset_resource_sizer.Add(self.save_dataset_button, pos=(3, 6), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL,
                                   border=2)

        ######################################
        # Build action sizer and logging box #
        ######################################

        toggle_execute_button = wx.Button(self.panel, wx.ID_ANY, label=u'Run Script')
        self.Bind(wx.EVT_BUTTON, self.OnRunScriptClicked, toggle_execute_button)
        save_config_button = wx.Button(self.panel, wx.ID_ANY, label=u'Save Script')
        self.Bind(wx.EVT_BUTTON, self.OnSaveScriptClicked, save_config_button)

        self.status_gauge = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.status_gauge.SetValue(0)
        self.status_gauge.SetMinSize(wx.Size(550, 25))

        self.log_message_listbox = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 110), [],
                                              wx.LB_EXTENDED)
        self.log_message_listbox.SetFont(wx.Font(9, 75, 90, 90, False, "Inconsolata"))
        self.log_message_listbox.SetMinSize(wx.Size(770, 75))
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnAvailableCategoryRightClick, self.log_message_listbox)

        action_status_sizer.Add(self.status_gauge, pos=(0, 0), span=(1, 8), flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND,
                                border=7)
        action_status_sizer.Add(toggle_execute_button, pos=(0, 9), span=(1, 1),
                                flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, border=7)
        action_status_sizer.Add(save_config_button, pos=(0, 8), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL | wx.EXPAND,
                                border=7)
        action_status_sizer.Add(self.log_message_listbox, pos=(1, 0), span=(2, 10),
                                flag=wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, border=7)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        main_sizer.Add(connections_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(selection_label_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(wx.StaticLine(self.panel), 0, flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border=15)
        main_sizer.Add(dataset_resource_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(wx.StaticLine(self.panel), 0, flag=wx.ALL | wx.EXPAND, border=15)
        main_sizer.Add(action_status_sizer, flag=wx.ALL | wx.EXPAND, border=5)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        file_menu = wx.Menu()
        file_menu.Append(wx.ID_ABOUT, "&About", " Information about this program")

        odm_connection_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage ODM Connections')
        resource_template_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage Resource Templates')
        hydroshare_account_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage HydroShare Accounts')

        self.Bind(wx.EVT_MENU, self.on_edit_database, odm_connection_menu_item)
        self.Bind(wx.EVT_MENU, self.OnEditResourceTemplates, resource_template_menu_item)
        self.Bind(wx.EVT_MENU, self.on_edit_hydroshare, hydroshare_account_menu_item)

        file_menu.Append(odm_connection_menu_item)
        file_menu.Append(resource_template_menu_item)
        file_menu.Append(hydroshare_account_menu_item)

        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, 'Quit', 'Quit application')

        # Menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")  # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        self.panel.SetSizerAndFit(main_sizer)
        self.SetAutoLayout(True)
        main_sizer.Fit(self.panel)
        self.panel.Fit()
        self.Fit()
        self.Show(True)

    def OnEditResourceTemplates(self, event):
        result = HydroShareResourceTemplateDialog(self, self.ActionManager.ResourceTemplates).ShowModal()
        event.Skip()

    def OnRunScriptClicked(self, event):
        self.OnPrintLog('Running script (almost)')

    def OnSaveScriptClicked(self, event):
        self.OnPrintLog('Saving the script')
        self.SaveData()

    def OnDatasetChoiceModified(self, event):
        if self.dataset_selector_choice.GetSelection() == 0:
            self.dataset_name_input.Value = ''
        else:
            self.dataset_name_input.Value = self.dataset_selector_choice.GetStringSelection()

        event.Skip()

    def GetLabel(self, label):
        return WxHelper.GetLabel(self.panel, label)
