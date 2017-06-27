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
from pubsub import pub
from Utilities.HydroShareUtility import HydroShareAccountDetails, HydroShareUtility, ResourceTemplate
from Utilities.DatasetGenerator import OdmDatasetConnection
from Utilities.H2OServices import H2OService, H2ODataset, OdmSeriesHelper, H20Series
# from Utilities.H2OServices import *
from Utilities.Odm2Wrapper import *
from GAMUTRawData.odmservices import ServiceManager
from EditConnectionsDialog import DatabaseConnectionDialog
from EditAccountsDialog import HydroShareAccountDialog
from WxUtilities import WxHelper, Orientation
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog
from InputValidator import *

service_manager = ServiceManager()

class CHOICE_DEFAULTS:
    NEW_TEMPLATE_CHOICE = 'Create a new resource template'
    SELECT_TEMPLATE_CHOICE = 'Select a resource template'

class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        ###########################################
        # Declare/populate variables, wx objects  #
        ###########################################
        self.MAIN_WINDOW_SIZE = (940, 860)
        self.WX_MONOSPACE = wx.Font(9, 75, 90, 90, False, "Inconsolata")
        self._setup_subscriptions()
        supported_notifications = ['logger', 'Dataset_Started', 'Dataset_Generated']
        self.H2OService = H2OService(subscriptions=supported_notifications)

        # self.ActiveOdmConnection = None  # type: # ServiceManager
        self.ActiveHydroshare = None  # type: HydroShareUtility

        self.odm_series_dict = {} # type: dict[str, Series]
        self.h2o_series_dict = {} # type: dict[str, H2OSeries]

        self._resources = None  # type: list[HydroShareResource]

        # Widgets
        self.status_gauge = None  # type: WxHelper.SimpleGauge
        self.database_connection_choice = None  # type: wx.Choice
        self.hydroshare_account_choice = None  # type: wx.Choice
        self.mapping_grid = None  # type: H20Widget
        self.available_series_listbox = None  # type: wx.ListBox

        # just technicalities, honestly
        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX,
                          size=self.MAIN_WINDOW_SIZE)
        self.parent = parent
        self.Centre()
        self._build_main_window()

        self.panel.Fit()
        self.Fit()
        self.Show(True)

        self.H2OService.LoadData()
        self.UpdateControls()

    def _setup_subscriptions(self):
        SUBSCRIPTIONS = [
            (self.OnDeleteResourceTemplate, 'hs_resource_remove'),
            (self.OnSaveResourceTemplate, 'hs_resource_save'),
            (self.OnSaveHydroShareAuth, 'hs_auth_save'),
            (self.OnTestHydroShareAuth, 'hs_auth_test'),
            (self.OnRemoveHydroShareAuth, 'hs_auth_remove'),
            (self.OnSaveDatabaseAuth, 'db_auth_save'),
            (self.OnTestDatabaseAuth, 'db_auth_test'),
            (self.OnRemoveDatabaseAuth, 'db_auth_remove'),
            (self.OnPrintLog, 'logger'),
            (self._update_status_gauge, 'Dataset_Started'),
            (self._update_status_gauge, 'Dataset_Generated')
        ]

        for sub_tuple in SUBSCRIPTIONS:
            pub.subscribe(sub_tuple[0], sub_tuple[1])

    def OnPrintLog(self, message=""):
        if message is None or not isinstance(message, str) or len(message) <= 1:
            return
        self.log_message_listbox.Insert('{}: {}'.format(datetime.datetime.now().strftime('%H-%M-%S'), message), 0)

    def UpdateControls(self, progress=None):
        if progress is not None:
            self.status_gauge = progress if 100 >= progress >= 0 else progress % 100
        WxHelper.UpdateChoiceControl(self.database_connection_choice, self._get_database_choices())
        WxHelper.UpdateChoiceControl(self.hydroshare_account_choice, self._get_hydroshare_choices())
        WxHelper.UpdateChoiceControl(self.hydroshare_resources_choice, self._get_dataset_choices())

    def OnDeleteResourceTemplate(self, result=None):
        if result is None:
            return
        self.H2OService.ResourceTemplates.pop(result['selector'], None)
        self.UpdateControls()
        self.H2OService.SaveData()

    def OnSaveResourceTemplate(self, result=None):
        if result is None:
            return
        template = ResourceTemplate(result)
        self.H2OService.ResourceTemplates.pop(result['selector'], None)
        self.H2OService.ResourceTemplates[template.template_name] = template
        self.UpdateControls()
        self.H2OService.SaveData()

    def OnRemoveDatabaseAuth(self, result=None):
        if result is None:
            return
        self.H2OService.DatabaseConnections.pop(result['selector'], None)
        self.UpdateControls()
        self.H2OService.SaveData()

    def OnSaveDatabaseAuth(self, result=None):
        if result is None:
            return
        connection = OdmDatasetConnection(result)
        self.H2OService.DatabaseConnections.pop(result['selector'], None)
        self.H2OService.DatabaseConnections[connection.name] = connection
        self.UpdateControls()
        self.H2OService.SaveData()

    def OnTestDatabaseAuth(self, result=None):
        if result is None:
            pub.sendMessage('db_auth_test_reply', reply='An error occurred, please try again later')
            return
        db_details = OdmDatasetConnection(result)
        if db_details.VerifyConnection():
            pub.sendMessage('db_auth_test_reply', reply='Successfully authenticated!')
        else:
            pub.sendMessage('db_auth_test_reply', reply='Authentication details were not accepted')

    def OnRemoveHydroShareAuth(self, result=None):
        if result is None:
            return
        self.H2OService.HydroShareConnections.pop(result['selector'], None)
        self.UpdateControls()
        self.H2OService.SaveData()

    def OnSaveHydroShareAuth(self, result=None):
        if result is None:
            return
        account = HydroShareAccountDetails(result)
        self.H2OService.HydroShareConnections.pop(result['selector'], None)
        self.H2OService.HydroShareConnections[account.name] = account
        self.UpdateControls()
        self.H2OService.SaveData()

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

    def _get_dataset_choices(self):
        if len(self.H2OService.Datasets) > 0:
            return ['Create a new dataset'] + list(self.H2OService.Datasets.keys())
        else:
            return ['Create a new dataset']

    def _get_hydroshare_choices(self):
        if len(self.H2OService.HydroShareConnections) > 0:
            return ['Select an account'] + [account for account in self.H2OService.HydroShareConnections.keys()]
        else:
            return ['No saved accounts']

    def _get_destination_resource_choices(self):
        if self.hydroshare_destination_radio.GetSelection() == 1 and self._resources is None:
            choices = ['Please connect to a HydroShare account']
        elif self.hydroshare_destination_radio.GetSelection() == 1 and len(self._resources) > 1:
            choices = ['Create a new resource'] + [item.title for item in self._resources]
        else:
            choices = [CHOICE_DEFAULTS.SELECT_TEMPLATE_CHOICE, CHOICE_DEFAULTS.NEW_TEMPLATE_CHOICE] + list(
                    [str(item) for item in self.H2OService.ResourceTemplates])
        return choices

    def _get_database_choices(self):
        if len(self.H2OService.DatabaseConnections) > 0:
            return ['Select a connection'] + [connection for connection in
                                              self.H2OService.DatabaseConnections.keys()]
        else:
            return ['No saved connections']

    def on_edit_database(self, event):
        result = DatabaseConnectionDialog(self, self.H2OService.DatabaseConnections,
                                          self.database_connection_choice.GetCurrentSelection()).ShowModal()

    def on_edit_hydroshare(self, event):
        result = HydroShareAccountDialog(self, self.H2OService.HydroShareConnections,
                                         self.hydroshare_account_choice.GetCurrentSelection()).ShowModal()

    def SetOdmConnection(self, connection):
        busy = wx.BusyInfo("Loading ODM series from database {}".format(connection.name))

        if connection.VerifyConnection():
            service_manager._current_connection = connection.ToDict()
            series_service = service_manager.get_series_service()
            series_list = series_service.get_all_series()
            for series in series_list:
                h2o_series = OdmSeriesHelper.CreateH2OSeriesFromOdmSeries(series)
                if h2o_series is None:
                    continue
                self.h2o_series_dict[str(h2o_series)] = h2o_series
                self.odm_series_dict[str(h2o_series)] = series
            self.UpdateSeriesInGrid()
        else:
            self.OnPrintLog('Unable to authenticate using connection {}'.format(connection.name))

    def SetHydroShareConnection(self, account_details):
        busy = wx.BusyInfo("Loading HydroShare account information for {}".format(account_details.name))
        try:
            self.ActiveHydroshare = HydroShareUtility()
            if self.ActiveHydroshare.authenticate(**account_details.to_dict()):
                self._resources = self.ActiveHydroshare.getAllResources()
                self.OnPrintLog('Successfully authenticated HydroShare account details')
            else:
                self.OnPrintLog('Unable to authenticate HydroShare account - please check your credentials')
        except:
            self.OnPrintLog('Unable to authenticate HydroShare account - please check your credentials')

    def on_database_chosen(self, event):
        self.available_series_listbox.Clear()
        self.selected_series_listbox.Clear()
        if event.GetSelection() > 0:
            self.h2o_series_dict.clear()
            selection_string = self.database_connection_choice.GetStringSelection()
            self.SetOdmConnection(self.H2OService.DatabaseConnections[selection_string])
        else:
            print "No selection made"

    def on_hydroshare_chosen(self, event):
        self._resources = None
        if event.GetSelection() != 0:
            self.OnPrintLog('Connecting to HydroShare')
            account_string = self.hydroshare_account_choice.GetStringSelection()
            self.SetHydroShareConnection(self.H2OService.HydroShareConnections[account_string])
        self._update_target_choices()

    def UpdateSeriesInGrid(self, event=None):
        if self.h2o_series_dict is None or len(self.h2o_series_dict) == 0:
            self.selected_series_listbox.SetItems(['No Selected Series'])
            self.selected_series_listbox.SetItems(['No Available Series'])
            self.remove_from_selected_button.Disable()
            self.add_to_selected_button.Disable()
            return

        self.available_series_listbox.Clear()
        for series_string in self.h2o_series_dict.keys():
            self.available_series_listbox.Append(series_string)

        self.remove_from_selected_button.Enable()
        self.add_to_selected_button.Enable()

    def _build_category_context_menu(self, selected_item, evt_parent):
        series_category_menu = wx.Menu()
        if self.h2o_series_dict is None or len(self.h2o_series_dict) == 0:
            return

        menu_strings = [u"Site: Select All", u"Site: Deselect All", u"Variable: Select All", u"Variable: Deselect All",
                        u"QC Code: Select All", u"QC Code: Deselect All"]
        listbox = self.selected_series_listbox if evt_parent == 'Selected Listbox' else self.available_series_listbox

        for text in menu_strings:
            WxHelper.AddNewMenuItem(self, series_category_menu, text, on_click=partial(self._category_selection,
                                                                                       control=listbox, direction=text,
                                                                                       curr_index=selected_item))
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
            self.available_series_listbox.Append(item)
            self.selected_series_listbox.Delete(self.selected_series_listbox.FindString(item))

        if len(self.selected_series_listbox.Items) == 0:
            self.selected_series_listbox.Append('No Selected Series')

    def OnAvailableCategoryRightClick(self, event):
        item_int = WxHelper.GetMouseClickIndex(event, self.available_series_listbox)
        if item_int >= 0:
            menu = self._build_category_context_menu(item_int, 'Available Listbox')
            if menu is not None:
                self.PopupMenu(menu)

    def OnSelectedCategoryRightClick(self, event):
        item_int = WxHelper.GetMouseClickIndex(event, self.selected_series_listbox)
        if item_int >= 0:
            self.PopupMenu(self._build_category_context_menu(item_int, 'Selected Listbox'))

    def _category_selection(self, event, direction, control, curr_index):
        category, action = direction.split(u': ')
        check_series = OdmSeriesHelper.PopulateH2OSeriesFromString(control.Items[curr_index])

        if check_series is None:
            print('Unable to parse information for {}'.format(control.Items[curr_index]))
            return

        for ctrl_index in range(0, len(control.Items)):
            temp_series = OdmSeriesHelper.PopulateH2OSeriesFromString(control.Items[ctrl_index])
            if OdmSeriesHelper.MATCH_ON_ATTRIBUTE[category](temp_series, check_series):
                if action == 'Select All':
                    control.Select(ctrl_index)
                elif action == 'Deselect All':
                    control.Deselect(ctrl_index)

    def _update_target_choices(self, event=None):
        WxHelper.UpdateChoiceControl(self.destination_resource_choice, self._get_destination_resource_choices())
        if event is not None:
            event.Skip()

    def _delete_dataset_clicked(self, event):
        dataset_name = self.hydroshare_resources_choice.GetStringSelection()
        if dataset_name in self.H2OService.Datasets:
            self.H2OService.Datasets.pop(dataset_name, None)
            self.hydroshare_resources_choice.SetSelection(0)
            WxHelper.UpdateChoiceControl(self.hydroshare_resources_choice, self._get_dataset_choices())

    def _copy_dataset_clicked(self, event):
        dataset_name = self.hydroshare_resources_choice.GetStringSelection()
        if dataset_name in self.H2OService.Datasets:
            self.hydroshare_resources_choice.SetSelection(0)
            counter = 1
            new_name = "{}_({})".format(self.dataset_name_input.Value, counter)
            while new_name in self.H2OService.Datasets and counter < 10:
                new_name = "{}_({})".format(self.dataset_name_input.Value, counter)
                counter += 1
            self.dataset_name_input.Value = new_name

    def _save_dataset_clicked(self, event):
        if not self._verify_dataset_selections():
            return

        series_items = []
        for item in self.selected_series_listbox.Items:
            check_series = OdmSeriesHelper.PopulateH2OSeriesFromString(item)
            if check_series is None or str(check_series) not in self.h2o_series_dict.keys():
                continue
            series_items.append(self.h2o_series_dict[str(check_series)])

        curr_dataset = H2ODataset(name=self.dataset_name_input.Value,
                                  odm_series=series_items,
                                  destination_resource=self.destination_resource_choice.GetStringSelection(),
                                  hs_account_name=self.hydroshare_account_choice.GetStringSelection(),
                                  odm_db_name=self.database_connection_choice.GetStringSelection(),
                                  create_resource=self.hydroshare_destination_radio.GetSelection() == 0,
                                  single_file=self.grouping_radio_buttons.GetSelection() == 1,
                                  chunk_by_year=self.chunk_by_year_checkbox.Value)

        # if we aren't making a new dataset, let's remove the old one from the dictionary
        dataset_name = self.hydroshare_resources_choice.GetStringSelection()
        if self.hydroshare_resources_choice.GetSelection() != 0 and dataset_name in self.H2OService.Datasets:
            self.H2OService.Datasets.pop(dataset_name, None)

        self.H2OService.Datasets[curr_dataset.name] = curr_dataset
        self.H2OService.SaveData()
        WxHelper.UpdateChoiceControl(self.hydroshare_resources_choice, self._get_dataset_choices())
        self.hydroshare_resources_choice.SetStringSelection(curr_dataset.name)

    def _verify_dataset_selections(self):
        if len(self.selected_series_listbox.Items) == 0:
            self.OnPrintLog('Invalid options - please select the ODM series you would like to add to the dataset')
        elif len(self.selected_series_listbox.Items) == 1 and self.selected_series_listbox.GetString(
                0) == 'No Selected Series':
            self.OnPrintLog('Invalid options - please select the ODM series you would like to add to the dataset')
        elif self.hydroshare_account_choice.GetSelection() == 0:
            self.OnPrintLog('Invalid options - please select a HydroShare account to use')
        elif self.hydroshare_destination_radio.GetSelection() == '1' and \
                        self.destination_resource_choice.GetSelection() == 0:
            self.OnPrintLog('Invalid options - please select a destination HydroShare resource or template')
        elif len(self.dataset_name_input.Value) == 0:
            self.OnPrintLog('Invalid options - please enter a dataset name')
        else:
            return True
        return False

    def OnEditResourceTemplates(self, event):
        result = HydroShareResourceTemplateDialog(self, self.H2OService.ResourceTemplates).ShowModal()

    def OnRunScriptClicked(self, event):
        self.OnPrintLog('Running script')
        self.H2OService.LoadData()
        self.H2OService.GenerateDatasetFiles()

    def OnStopScriptClicked(self, event):
        self.OnPrintLog('Stopping the script')
        self.H2OService.StopActions()

    def SetAsActiveDataset(self, dataset):
        """

        :type dataset: H20Dataset
        """
        self.OnPrintLog('Fetching information for dataset {}'.format(dataset.name))

        if dataset.odm_db_name != self.database_connection_choice.GetStringSelection():
            if dataset.odm_db_name in self.H2OService.DatabaseConnections:
                self.database_connection_choice.SetStringSelection(dataset.odm_db_name)
                self.SetOdmConnection(self.H2OService.DatabaseConnections[dataset.odm_db_name])
            else:
                self.OnPrintLog('Error loading ODM series: Unknown connection {}'.format(dataset.odm_db_name))
                return

        if dataset.hs_account_name != self.hydroshare_account_choice.GetStringSelection():
            if dataset.hs_account_name in self.H2OService.HydroShareConnections:
                self.hydroshare_account_choice.SetStringSelection(dataset.hs_account_name)
                self.SetHydroShareConnection(self.H2OService.HydroShareConnections[dataset.hs_account_name])
            else:
                self.OnPrintLog('HydroShare account error: Unknown connection {}'.format(dataset.hs_account_name))
                self.hydroshare_account_choice.SetSelection(0)
                self.OnPrintLog('To resolve, select a HydroShare account and save dataset')

        selected = []
        available = []

        for series in self.h2o_series_dict.keys():
            if series in dataset.odm_series:
                selected.append(str(series))
            else:
                available.append(str(series))

        self.available_series_listbox.SetItems(available)
        self.selected_series_listbox.SetItems(selected)

        self.dataset_name_input.Value = dataset.name
        self.hydroshare_resources_choice.SetStringSelection(dataset.name)
        self.hydroshare_destination_radio.SetSelection(0 if dataset.create_resource else 1)
        self._update_target_choices()  # Update these before we try to set our destination
        self.destination_resource_choice.SetStringSelection(dataset.destination_resource)
        self.grouping_radio_buttons.SetSelection(0 if dataset.single_file else 1)
        self.chunk_by_year_checkbox.Value = dataset.chunk_by_year

    def OnDatasetChoiceModified(self, event):
        if self.hydroshare_resources_choice.GetStringSelection() in self.H2OService.Datasets:
            dataset = self.H2OService.Datasets[self.hydroshare_resources_choice.GetStringSelection()]
            self.SetAsActiveDataset(dataset)
        event.Skip()

    def _destination_resource_changed(self, event):
        if self.destination_resource_choice.GetStringSelection() == CHOICE_DEFAULTS.NEW_TEMPLATE_CHOICE:
            self.OnEditResourceTemplates(None)

    def _update_status_gauge(self, resource, completed=None, started=None):
        message = ' generating files for resource {}'.format(resource)
        state = 'None'
        if completed is not None:
            state = 'Finished'
            self.status_gauge.SetValue(completed)
        elif started is not None:
            state = 'Starting'
            self.status_gauge.SetValue(started)

        self.OnPrintLog(state + message)

    def GetLabel(self, label, font=None):
        return WxHelper.GetLabel(self.panel, label, font)

    def _build_main_window(self):
        ######################################
        #   Setup sizers and panels          #
        ######################################
        self.panel = wx.Panel(self, wx.ID_ANY)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = WxHelper.GetGridBagSizer()
        selection_label_sizer = WxHelper.GetGridBagSizer()
        dataset_sizer = WxHelper.GetGridBagSizer()
        action_status_sizer = WxHelper.GetGridBagSizer()

        ######################################
        #   Build connection details sizer   #
        ######################################
        edit_database_button = WxHelper.GetButton(self, self.panel, u'Edit...', on_click=self.on_edit_database)
        edit_hydroshare_button = WxHelper.GetButton(self, self.panel, u'Edit...', on_click=self.on_edit_hydroshare)

        self.database_connection_choice = WxHelper.GetChoice(self, self.panel, self._get_database_choices(),
                                                             on_change=self.on_database_chosen, size_x=310, size_y=23)
        self.hydroshare_account_choice = WxHelper.GetChoice(self, self.panel, self._get_hydroshare_choices(),
                                                            on_change=self.on_hydroshare_chosen, size_x=310, size_y=23)

        connections_sizer.Add(self.GetLabel(u'Select a database connection'), pos=(0, 0),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.EXPAND | wx.RIGHT, border=7)
        connections_sizer.Add(self.database_connection_choice, pos=(1, 0), span=(1, 4),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=7)
        connections_sizer.Add(edit_database_button, pos=(1, 4), span=(1, 1),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT, border=7)

        connections_sizer.Add(self.GetLabel(u'Select a HydroShare account'), pos=(0, 8),
                              span=(1, 4), flag=wx.ALIGN_LEFT | wx.LEFT | wx.EXPAND | wx.RIGHT, border=15)
        connections_sizer.Add(self.hydroshare_account_choice, pos=(1, 8), span=(1, 4),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=15)
        connections_sizer.Add(edit_hydroshare_button, pos=(1, 12), span=(1, 1),
                              flag=wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT, border=15)

        ######################################
        # Build selection sizer and objects  #
        ######################################

        self.selected_series_listbox = WxHelper.GetListBox(self, self.panel, ['No Selected Series'],
                                                           on_right_click=self.OnSelectedCategoryRightClick, size_x=375,
                                                           size_y=200, font=self.WX_MONOSPACE)
        self.available_series_listbox = WxHelper.GetListBox(self, self.panel, ['No Available Series'], flags=wx.LB_EXTENDED | wx.LB_SORT,
                                                            on_right_click=self.OnAvailableCategoryRightClick,
                                                            size_x=375, size_y=200, font=self.WX_MONOSPACE)

        self.grouping_radio_buttons = WxHelper.GetRadioBox(self.panel, u"Series File Grouping",
                                                           [u"Single File for all series", u"One file per series"])

        self.chunk_by_year_checkbox = wx.CheckBox(self.panel, wx.ID_ANY, u"Chunk file(s) by year", wx.Point(-1, -1),
                                                  wx.DefaultSize, 0)

        self.hydroshare_destination_radio = WxHelper.GetRadioBox(self.panel, u"HydroShare Resource",
                                                                 [u"Create new resource from template",
                                                                  u"Use an existing HydroShare resource"])
        self.hydroshare_destination_radio.SetSelection(1)
        self.Bind(wx.EVT_RADIOBOX, self._update_target_choices, self.hydroshare_destination_radio)

        self.destination_resource_choice = WxHelper.GetChoice(self, self.panel,
                                                              self._get_destination_resource_choices(),
                                                              on_change=self._destination_resource_changed)

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
        self.save_dataset_button = WxHelper.GetButton(self, self.panel, u" Save Dataset ", self._save_dataset_clicked,
                                                      size_x=100, size_y=30)
        self.copy_dataset_button = WxHelper.GetButton(self, self.panel, u" Copy Dataset ", self._copy_dataset_clicked,
                                                      size_x=100, size_y=30)
        self.delete_dataset_button = WxHelper.GetButton(self, self.panel, u"Delete Dataset",
                                                        self._delete_dataset_clicked, size_x=100, size_y=30)

        # Dataset choice and input
        self.hydroshare_resources_choice = WxHelper.GetChoice(self, self.panel, self._get_dataset_choices(),
                                                              on_change=self.OnDatasetChoiceModified)

        self.dataset_name_input = wx.TextCtrl(self.panel, wx.ID_ANY, u'', wx.DefaultPosition, wx.DefaultSize, 7,
                                              validator=CharValidator(PATTERNS.CV_WORD))
        self.dataset_name_input.SetMinSize(wx.Size(275, 25))

        ###################################################
        # Most things, but with the options all on left   #
        ###################################################

        series_label = u'Site                    Variable                  QC Level   Source  Method'
        dataset_sizer.Add(self.GetLabel(series_label, font=self.WX_MONOSPACE), pos=(7, 0), span=(1, 3),
                          flag=wx.ALIGN_LEFT | wx.LEFT, border=10)
        dataset_sizer.Add(self.GetLabel(series_label, font=self.WX_MONOSPACE), pos=(7, 5), span=(1, 4),
                          flag=wx.ALIGN_LEFT | wx.RIGHT, border=12)
        dataset_sizer.Add(self.GetLabel(u'Available Series'), pos=(6, 0), span=(1, 3), flag=wx.ALIGN_CENTER | wx.TOP, border=8)
        dataset_sizer.Add(self.GetLabel(u'Selected Series'), pos=(6, 5), span=(1, 4), flag=wx.ALIGN_CENTER | wx.TOP, border=8)
        dataset_sizer.Add(self.available_series_listbox, pos=(8, 0), span=(6, 4),
                          flag=wx.ALIGN_CENTER | wx.LEFT | wx.EXPAND, border=7)
        dataset_sizer.Add(self.selected_series_listbox, pos=(8, 5), span=(6, 4),
                          flag=wx.ALIGN_CENTER | wx.RIGHT | wx.EXPAND, border=7)
        dataset_sizer.Add(self.add_to_selected_button, pos=(10, 4), span=(1, 1),
                          flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=2)
        dataset_sizer.Add(self.remove_from_selected_button, pos=(11, 4), span=(1, 1),
                          flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.TOP, border=2)

        # dataset_sizer.Add(self.GetLabel(u'HydroShare Resources'), pos=(0, 0), span=(1, 1),
        dataset_sizer.Add(self.GetLabel(u'Select a dataset'), pos=(0, 0), span=(1, 1),
                                            flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.TOP, border=7)
        dataset_sizer.Add(self.hydroshare_resources_choice, pos=(1, 0), span=(1, 4),
                          flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=7)
        dataset_sizer.Add(self.GetLabel(u'Name'), pos=(0, 5), span=(1, 1),
                          flag=wx.ALIGN_CENTER | wx.RIGHT | wx.EXPAND | wx.TOP, border=7)
        dataset_sizer.Add(self.dataset_name_input, pos=(1, 5), span=(1, 4), flag=wx.ALIGN_LEFT | wx.EXPAND | wx.RIGHT,
                          border=7)

        dataset_sizer.Add(connections_sizer, pos=(2, 0), span=(1, 9),
                          flag=wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, border=7)

        dataset_sizer.Add(self.GetLabel(u'Upload dataset to...'), pos=(4, 0), span=(1, 1),
                          flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT, border=7)
        dataset_sizer.Add(self.hydroshare_destination_radio, pos=(3, 0), span=(1, 4),
                          flag=wx.ALIGN_LEFT | wx.LEFT | wx.TOP,
                          border=5)

        dataset_sizer.Add(self.destination_resource_choice, pos=(5, 0), span=(1, 4),
                          flag=wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, border=5)

        dataset_sizer.Add(self.grouping_radio_buttons, pos=(3, 5), span=(1, 3), flag=wx.ALIGN_LEFT | wx.ALL, border=7)
        dataset_sizer.Add(self.chunk_by_year_checkbox, pos=(3, 8), span=(1, 1), flag=wx.ALIGN_CENTER | wx.RIGHT,
                          border=7)

        dataset_sizer.Add(self.delete_dataset_button, pos=(5, 8), span=(1, 1), flag=wx.ALIGN_LEFT | wx.ALL, border=2)
        dataset_sizer.Add(self.copy_dataset_button, pos=(5, 7), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL, border=2)
        dataset_sizer.Add(self.save_dataset_button, pos=(5, 6), span=(1, 1), flag=wx.ALIGN_CENTER | wx.ALL, border=2)

        ######################################
        # Build action sizer and logging box #
        ######################################

        toggle_execute_button = WxHelper.GetButton(self, self.panel, u"Run Script", self.OnRunScriptClicked)
        save_config_button = WxHelper.GetButton(self, self.panel, u"Stop Script", self.OnStopScriptClicked)

        self.status_gauge = wx.Gauge(self.panel, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.status_gauge.SetValue(0)
        # self.status_gauge.SetMinSize(wx.Size(550, 25))

        self.log_message_listbox = WxHelper.GetListBox(self, self.panel, [], size_x=920, size_y=150,
                                                       font=self.WX_MONOSPACE)

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

        # main_sizer.Add(connections_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(selection_label_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        # main_sizer.Add(wx.StaticLine(self.panel), 0, flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border=15)
        main_sizer.Add(dataset_sizer, flag=wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(wx.StaticLine(self.panel), 0, flag=wx.ALL | wx.EXPAND, border=15)
        main_sizer.Add(action_status_sizer, flag=wx.ALL | wx.EXPAND, border=5)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        file_menu = wx.Menu()

        WxHelper.AddNewMenuItem(self, file_menu, u'ODM Connections...', self.on_edit_database)
        WxHelper.AddNewMenuItem(self, file_menu, u'HydroShare Accounts...', self.on_edit_hydroshare)
        WxHelper.AddNewMenuItem(self, file_menu, u'Resource Templates...', self.OnEditResourceTemplates)

        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, 'Quit', 'Quit application')

        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")  # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        self.panel.SetSizerAndFit(main_sizer)
        self.SetAutoLayout(True)
        main_sizer.Fit(self.panel)
