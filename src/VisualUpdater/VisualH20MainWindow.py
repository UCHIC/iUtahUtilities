
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
from Utilities.Odm2Wrapper import *
from GAMUTRawData.odmservices import ServiceManager
from EditConnectionsDialog import DatabaseConnectionDialog
from EditAccountsDialog import HydroShareAccountDialog
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog
from H20MapWidget import H20MapWidget
from ResourceTemplatesDialog import HydroShareResourceTemplateDialog


PERSIST_FILE = './persist_file'
service_manager = ServiceManager()

class VisualH2OWindow(wx.Frame):
    def __init__(self, parent, id, title):
        ###########################################
        # Declare/populate variables, wx objects  #
        ###########################################
        self.MAIN_WINDOW_SIZE = (1024, 720)
        self.HydroShareConnections = {}
        self.DatabaseConnections = {}
        self.ResourceTemplates = {}

        self.ActiveOdmConnection = None  # type: ServiceManager
        self.ActiveHydroshare = None     # type: HydroShareUtility

        self._series_list = None              # type: list
        # self._series_dict = None              # type: dict
        self._resources = None                # type: dict

        self.series_keys = ['SiteCode', 'SiteName', 'VariableCode', 'VariableName', 'Speciation', 'VariableUnitsName',
                            'SampleMedium', 'ValueType', 'TimeSupport', 'TimeUnitsName', 'DataType', 'GeneralCategory',
                            'MethodDescription', 'SourceDescription', 'Organization', 'Citation',
                            'QualityControlLevelCode', 'BeginDateTime', 'EndDateTime', 'BeginDateTimeUTC',
                            'EndDateTimeUTC', 'ValueCount']

        # Load persistence file
        try:
            self.LoadData()
        except:
            print "This looks like a first run"

        # Widgets
        self.status_gauge = None              # type: wx.Gauge
        self.select_database_choice = None    # type: wx.Choice
        self.select_hydroshare_choice = None  # type: wx.Choice
        self.odm2_series_display = None       # type: wx.ListBox
        # self.hydroshare_display = None        # type: # wx.ListCtrl
        self.hydroshare_display = None        # type: wx.ListBox
        self.series_view_selector = None      # type: wx.Choice

        # just technicalities, honestly
        wx.Frame.__init__(self, parent, id, title, style=wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.CAPTION | wx.CLOSE_BOX, size=self.MAIN_WINDOW_SIZE)
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

    def SaveData(self):
        self.UpdateControls()
        data = {'HS': self.HydroShareConnections, 'DB': self.DatabaseConnections, 'Templates': self.ResourceTemplates}
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
            self.ResourceTemplates = data['Templates'] if 'Templates' in data else {}
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

        # if self.odm2_series_display is not None:
        # self.populate_series_list()

        if self.hydroshare_display is not None:
            pass

    def OnDeleteResourceTemplate(self, result=None):
        if result is None:
            return
        self.ResourceTemplates.pop(result['selector'], None)
        self.SaveData()

    def OnSaveResourceTemplate(self, result=None):
        if result is None:
            return
        template = ResourceTemplate(result)
        self.ResourceTemplates.pop(result['selector'], None)
        self.ResourceTemplates[template.template_name] = template
        self.SaveData()

    def OnRemoveDatabaseAuth(self, result=None):
        if result is None:
            return
        self.DatabaseConnections.pop(result['selector'], None)
        self.SaveData()

    def OnSaveDatabaseAuth(self, result=None):
        if result is None:
            return
        connection = OdmDatasetUtility(result)
        self.DatabaseConnections.pop(result['selector'], None)
        self.DatabaseConnections[connection.name] = connection
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
        result = DatabaseConnectionDialog(self, self.DatabaseConnections, self.select_database_choice.GetCurrentSelection()).ShowModal()

    def on_edit_hydroshare(self, event, accounts=None):
        result = HydroShareAccountDialog(self, self.HydroShareConnections, self.select_hydroshare_choice.GetCurrentSelection()).ShowModal()

    def on_database_chosen(self, event):
        if event.GetSelection() > 0:
            print "Lets connect"
            selection_string = self.select_database_choice.GetStringSelection()
            print selection_string
            connection = self.DatabaseConnections[selection_string]
            if connection.VerifyConnection():
                service_manager._current_connection = connection.ToDict()
                series_service = service_manager.get_series_service()
                self._series_list = [series.dict_repr() for series in series_service.get_all_series()]
                # all_series = series_service.get_all_series()
                # for series in all_series:
                #     self._series[series.site_code] = series
                # self._series_list = [series_service.get_all_series()]
                # for item in self._series_list:
                #     self._series_dict
                self.populate_dataset_tree()
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
                self.hydroshare_display.Append(self.ActiveHydroshare.resource_cache[resource].name)
        event.Skip()

    # def populate_series_list(self, event=None):
    #     view_as = self.series_view_selector.GetStringSelection()
    #     if self._series is None:
    #         return
    #     self.odm2_series_display.Clear()
    #     items = set([series.dict_repr()[view_as] for series in self._series])
    #     for item in items:
    #         self.odm2_series_display.Append(str(item))

    def AddTree(self, treeId, dict):
        if len(dict) > 0:
            for key in set(dict.keys()):
                newId = self.dataset_preview_tree.AppendItem(treeId, key)
                self.AddTree(newId, dict[key])

    def BuildDatasetDictionary(self, categories, layer=0):
        layer_dict = {}
        if layer >= len(categories):
            return {}

        # previous_attributes = categories[layer:]
        # current_attribute = categories[layer]
        # attribute_values = set([str(series[current_attribute]) for series in self._series_list])
        # #
        # tree_dict = {}
        #
        #
        # print layer
        # print categories

        keys = set([str(series[categories[layer]]) for series in self._series_list])
        for key in keys:
            layer_dict[key] = self.BuildDatasetDictionary(categories, layer + 1)
        return layer_dict

    def _resolve_dataset_conflicts(self, checked_index):
        conflicts = {'SiteCode': 'SiteName', 'SiteName': 'SiteCode', 'VariableCode': 'VariableName', 'VariableName': 'VariableCode'}
        checked_string = self.series_categories_checklist.GetString(checked_index)
        if checked_string in conflicts.keys():
            conflict_index = self.series_categories_checklist.FindString(conflicts[checked_string])
            if self.series_categories_checklist.IsChecked(conflict_index):
                self.series_categories_checklist.Check(conflict_index, check=False)
                self._MoveListItem(curr_index=conflict_index, dest_index=len(self.series_categories_checklist.GetCheckedItems()))

    def populate_dataset_tree(self, event=None):
        checked_strings = list(self.series_categories_checklist.GetCheckedStrings())
        # checked_count = len(checked_strings)
        # if event is not None:
        #     if self.series_categories_checklist.IsChecked(event.GetInt()):
        #         # self._resolve_dataset_conflicts(event.GetInt())
        #         self._MoveListItem(curr_index=event.GetInt(), dest_index=checked_count - 1)
        #     else:
        #         self._MoveListItem(curr_index=event.GetInt(), dest_index=checked_count)
        self.dataset_preview_tree.DeleteAllItems()

        if self._series_list is None or len(checked_strings) == 0:
            # self.mapping_grid.ClearGrid()
            return
        # self.dataset_preview_tree.DeleteAllItems()
        root = self.dataset_preview_tree.AddRoot('root')

        super_new_dicts = defaultdict(list)
        for d in self._series_list:
            for k, l in d.items():
                if isinstance(l, list):
                    for value in l:
                        super_new_dicts[str(value)].append(k)
                else:
                    super_new_dicts[str(l)].append(k)

        print(super_new_dicts)
        self.AddTree(root, super_new_dicts)

        # raise Exception('uberexception')

        #
        # strings = []
        # category_tree = {}
        #
        # for category in checked_strings:
        #     set
        #
        #
        #
        # for series in self._series_list:
        #     my_root = root
        #     for category in checked_strings:
        #         if series[category] in category_tree:
        #             continue
        #         else:
        #
        #             my_root = self.dataset_preview_tree.AppendItem(series[category])
        #

        dict_1 = {}
        #
        # for series in self._series_list:
        #     for category in checked_strings:
        #         if dict_1.keys:


        tree_dict = {}
        #
        # for series in self._series_list:
        #     root_string = "Your_String_Here"
        #     for category in checked_strings:
        #         root_string += "_" + series[category]
        #     strings.append(root_string)

        # for string in strings:
        #     print string

        # tree_dict = self.BuildDatasetDictionary(checked_strings)
        # self.mapping_grid.Recreate(tree_dict)

        # self.AddTree(root, tree_dict)
        # event.Skip()


    def OnCategoryDoubleClick(self, event):
        checked = self.series_categories_checklist.IsChecked(event.GetInt())
        self.series_categories_checklist.Check(event.GetInt(), check=not checked)
        checked_count = len(self.series_categories_checklist.GetCheckedItems())
        if self.series_categories_checklist.IsChecked(event.GetInt()):
            self._MoveListItem(curr_index=event.GetInt(), dest_index=checked_count - 1)
        else:
            self._MoveListItem(curr_index=event.GetInt(), dest_index=checked_count)
        self.populate_dataset_tree(event)
        event.Skip()

    def _build_category_context_menu(self, selected_item):
        series_category_menu = wx.Menu()
        series_category_menu.AppendItem(wx.MenuItem(series_category_menu, wx.ID_ANY, u"Move to root", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.AppendItem(wx.MenuItem(series_category_menu, wx.ID_ANY, u"Move up once", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.AppendItem(wx.MenuItem(series_category_menu, wx.ID_ANY, u"Move down once", wx.EmptyString, wx.ITEM_NORMAL))
        series_category_menu.AppendItem(wx.MenuItem(series_category_menu, wx.ID_ANY, u"Move to tail", wx.EmptyString, wx.ITEM_NORMAL))

        for item in series_category_menu.GetMenuItems():
            self.Bind(wx.EVT_MENU, partial(self._MoveListItem, direction=item.GetText(), curr_index=selected_item), item)

    def OnCategoryRightClick(self, event):
        evt_pos = event.GetPosition()
        list_pos = self.series_categories_checklist.ScreenToClient(evt_pos)
        item_int = self.series_categories_checklist.HitTest(list_pos)
        if item_int >= 0:
            self.series_categories_checklist.SetSelection(item_int)
            self.PopupMenu(self._build_category_context_menu(item_int))
        event.Skip()

    def _MoveListItem(self, event=None, direction="None", curr_index=-1, dest_index=-1):
        item_count = len(self.series_categories_checklist.Items)

        if dest_index == -1: # or send_to_border:
            if direction == u'Move to root':
                dest_index = 0
            elif direction == u'Move up once' and curr_index > 0:
                dest_index = curr_index - 1
            elif direction == u'Move down once' and curr_index < item_count:
                dest_index = curr_index + 1
            elif direction == u'Move to tail':
                dest_index = item_count - 1

        while  0 <= curr_index < item_count and dest_index != curr_index:
            next_move = curr_index - 1 if dest_index < curr_index else curr_index + 1
            dest_checked = self.series_categories_checklist.IsChecked(next_move)    # Is my next move checked?
            dest_string = self.series_categories_checklist.GetString(next_move)     # Save the destination string
            self.series_categories_checklist.SetString(next_move, self.series_categories_checklist.GetString(curr_index))      #
            self.series_categories_checklist.Check(next_move, check=self.series_categories_checklist.IsChecked(curr_index))  #
            self.series_categories_checklist.Check(curr_index, check=dest_checked)
            self.series_categories_checklist.SetString(curr_index, dest_string)     #
            curr_index += -1 if dest_index < curr_index else 1

        self.populate_dataset_tree()
        self.series_categories_checklist.Refresh()

    def _build_main_window(self):
        ######################################
        #   Setup sizers and panels          #
        ######################################
        self.panel = wx.Panel(self, wx.ID_ANY)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        connections_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        selection_label_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        dataset_resource_sizer = wx.GridBagSizer(vgap=7, hgap=7)
        dataset_resource_sizer_new = wx.GridBagSizer(vgap=7, hgap=7)
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

        self.series_categories_checklist = wx.CheckListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, self.series_keys)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnCategoryDoubleClick, self.series_categories_checklist)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnCategoryRightClick, self.series_categories_checklist)
        self.Bind(wx.EVT_CHECKLISTBOX, self.populate_dataset_tree, self.series_categories_checklist)



        # self.dataset_preview_tree = wx.TreeCtrl(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        # self.dataset_preview_tree.SetMinSize(wx.Size(300, 250))



        # self.odm2_series_display = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [], wx.LB_MULTIPLE|wx.LB_NEEDED_SB|wx.LB_SORT )
        # self.odm2_series_display.SetMinSize(wx.Size(360, 150))
        # self.odm2_series_display.SetMaxSize(wx.Size(320, 150))

        # self.hydroshare_display = wx.ListBox(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [], wx.LB_MULTIPLE|wx.LB_NEEDED_SB|wx.LB_SORT )
        # self.hydroshare_display.SetMinSize(wx.Size(360, 150))
        # self.hydroshare_display.SetMaxSize(wx.Size(320, 150))

        # self.mapping_grid = wx.grid.Grid(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # self.mapping_grid = H20MapWidget(self.panel, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, rows=4, columns=6)

        # Label Appearance

        # Cell Defaults
        # self.mapping_grid.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # self.Bind(wx.grid.E)

        self.dataset_preview_tree = wx.TreeCtrl(self.panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self.dataset_preview_tree.SetMinSize(wx.Size(300, 250))


        self.series_view_selector = wx.Choice(self.panel, wx.ID_ANY, choices=self.series_keys)
        self.series_view_selector.SetSelection(0)
        # self.Bind(wx.EVT_CHOICE, self.populate_series_list, self.series_view_selector)

        dataset_resource_sizer_new.Add(wx.StaticText(self.panel, wx.ID_ANY, 'View ODM Series as'), pos=(0, 0), span=(1, 1), flag=wx.ALIGN_CENTER | wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, border=10)
        dataset_resource_sizer_new.Add(self.series_view_selector, pos=(0, 1), span=(1, 1), flag=wx.ALIGN_CENTER | wx.EXPAND | wx.RIGHT | wx.TOP, border=7)
        dataset_resource_sizer_new.Add(wx.StaticText(self.panel, wx.ID_ANY, 'HydroShare Resources'), pos=(0, 2), span=(1, 2), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.RIGHT | wx.EXPAND | wx.ALL, border=7)
        dataset_resource_sizer_new.Add(self.series_categories_checklist, pos=(1, 0), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND | wx.ALL, border=7)
        # dataset_resource_sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, 'View series as'), pos=(2, 0), span=(1, 1), flag=wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT | wx.EXPAND | wx.ALL, border=7)
        # dataset_resource_sizer_new.Add(self.mapping_grid, pos=(1, 1), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND | wx.ALL, border=7)
        dataset_resource_sizer_new.Add(self.dataset_preview_tree, pos=(1, 1), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND | wx.ALL, border=7)
        # dataset_resource_sizer_new.Add(self.odm2_series_display, pos=(1, 1), span=(1, 1), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND | wx.ALL, border=7)
        # dataset_resource_sizer_new.Add(self.mapping_grid, pos=(1, 2), span=(1, 2), flag=wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT | wx.EXPAND | wx.ALL, border=7)


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
        # main_sizer.Add(data_management_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(dataset_resource_sizer, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(dataset_resource_sizer_new, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(action_status_sizer, wx.EXPAND | wx.ALL, 5)

        ######################################
        # Build menu bar and setup callbacks #
        ######################################

        # File menu
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_ABOUT, "&About", " Information about this program")

        resource_template_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage Resource Templates')
        self.Bind(wx.EVT_MENU, self.OnEditResourceTemplates, resource_template_menu_item)
        file_menu.Append(resource_template_menu_item)


        odm_connection_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage ODM Connections')
        self.Bind(wx.EVT_MENU, self.on_edit_database, odm_connection_menu_item)
        file_menu.Append(odm_connection_menu_item)


        hydroshare_account_menu_item = wx.MenuItem(file_menu, wx.ID_ANY, u'Manage HydroShare Accounts')
        self.Bind(wx.EVT_MENU, self.on_edit_hydroshare, hydroshare_account_menu_item)
        file_menu.Append(hydroshare_account_menu_item)

        file_menu.AppendSeparator()
        file_menu.Append(wx.ID_EXIT, 'Quit', 'Quit application')

        # Menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(file_menu, "&File")  # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        self.panel.SetSizerAndFit(main_sizer)
        self.Show(True)

    def OnEditResourceTemplates(self, event):
        result = HydroShareResourceTemplateDialog(self, self.ResourceTemplates).ShowModal()
        print result
        event.Skip()


    def OnButtonClick(self, event):
        print "You clicked the button !"
        event.Skip()


    def OnPressEnter(self, event):
        print "You pressed enter !"
        event.Skip()
