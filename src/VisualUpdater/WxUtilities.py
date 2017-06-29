import wx
from InputValidator import *
# import wx.dataview
# import wx.grid

class Orientation:
    VERTICAL = 1
    HORIZONTAL = 0


class WxHelper:
    @staticmethod
    def GetFlags(flags=0, expand=True, top=True, bottom=True, left=True, right=True):
        flags |= wx.EXPAND if expand else 0
        flags |= wx.TOP if top else 0
        flags |= wx.LEFT if left else 0
        flags |= wx.RIGHT if right else 0
        flags |= wx.BOTTOM if bottom else 0
        return flags

    @staticmethod
    def GetBitmap(path, size_x=None, size_y=None):
        image = wx.Bitmap.ConvertToImage(wx.Bitmap(path, wx.BITMAP_TYPE_ANY))
        if size_x is not None and size_y is not None:
            image = image.Scale(size_x, size_y, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    @staticmethod
    def GetGridBagSizer(padding_x=8, padding_y=8):
        sizer = wx.GridBagSizer(vgap=padding_y, hgap=padding_x)
        sizer.SetFlexibleDirection(direction=wx.BOTH)
        sizer.SetNonFlexibleGrowMode(mode=wx.FLEX_GROWMODE_ALL)
        return sizer

    @staticmethod
    def GetRadioBox(parent, label, options, orientation=Orientation.VERTICAL):
        radiobox = wx.RadioBox(parent, wx.ID_ANY, label, wx.DefaultPosition, wx.DefaultSize, options, orientation,
                               wx.RA_SPECIFY_ROWS)
        radiobox.SetSelection(0)
        return radiobox

    @staticmethod
    def GetWxSize(size_x, size_y):
        size_x = -1 if size_x is None else size_x
        size_y = -1 if size_y is None else size_y
        return wx.Size(size_x, size_y)

    @staticmethod
    def GetTextInput(parent, placeholder_text=u'', size_x=None, size_y=None, validator=CharValidator(PATTERNS.ANY),
                     max_length=None, wrap_text=False):
        if wrap_text:
            text_ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=placeholder_text, pos=wx.DefaultPosition, size=wx.DefaultSize,
                                    style=wx.TE_BESTWRAP | wx.TE_MULTILINE, validator=validator)
        else:
            text_ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=placeholder_text, pos=wx.DefaultPosition, size=wx.DefaultSize,
                                    style=7, validator=validator)
        text_ctrl.SetMinSize(WxHelper.GetWxSize(size_x, size_y))
        text_ctrl.SetMaxSize(WxHelper.GetWxSize(size_x, size_y))
        if max_length is not None:
            text_ctrl.SetMaxLength(max_length)
        return text_ctrl

    @staticmethod
    def GetListBox(app, parent, items, on_right_click=None, size_x=None, size_y=None, font=None, flags=wx.LB_EXTENDED):
        listbox = wx.ListBox(parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, items, flags)
        if size_x is not None and size_y is not None:
            listbox.SetMinSize(wx.Size(size_x, size_y))
            listbox.SetMaxSize(wx.Size(size_x, size_y))
        if font is not None:
            listbox.SetFont(font)
        if on_right_click is not None:
            app.Bind(wx.EVT_CONTEXT_MENU, on_right_click, listbox)
        return listbox

    @staticmethod
    def GetButton(app, parent, label, on_click=None, size_x=None, size_y=None):
        button = wx.Button(parent, wx.ID_ANY, label, wx.DefaultPosition, wx.DefaultSize, 0)
        if size_x is not None and size_y is not None:
            button.SetMinSize(wx.Size(size_x, size_y))
            button.SetMaxSize(wx.Size(size_x, size_y))
        if on_click is not None:
            app.Bind(wx.EVT_BUTTON, on_click, button)
        return button

    @staticmethod
    def GetChoice(app, parent, choices, on_change=None, size_x=None, size_y=None):
        choice = wx.Choice(parent, wx.ID_ANY, choices=choices)

        if size_x is not None and size_y is not None:
            choice.SetMinSize(wx.Size(size_x, size_y))
            choice.SetMaxSize(wx.Size(size_x, size_y))
        if on_change is not None:
            app.Bind(wx.EVT_CHOICE, on_change, choice)

        choice.SetSelection(0)
        return choice

    @staticmethod
    def GetLabel(parent, text, font=None):
        label = wx.StaticText(parent, wx.ID_ANY, text)
        if font is not None:
            label.SetFont(font)
        return label

    @staticmethod
    def AddNewMenuItem(app, menu, label, on_click=None, return_item=False):
        menu_item = wx.MenuItem(menu, wx.ID_ANY, label)
        if on_click is not None:
            app.Bind(wx.EVT_MENU, on_click, menu_item)
        menu.Append(menu_item)
        if return_item:
            return menu_item

    @staticmethod
    def UpdateChoiceControl(control, choices):
        if control is not None and choices is not None:
            db_index = control.GetCurrentSelection()
            db_name = control.GetStringSelection()

            control.Clear()
            control.SetItems(choices if isinstance(choices, list) else list(choices))

            string_index = control.FindString(db_name)
            if string_index >= 0:
                control.SetSelection(string_index)
            elif db_index < len(control.Items):
                control.SetSelection(db_index)
            else:
                control.SetSelection(0)

    @staticmethod
    def GetMouseClickIndex(event, control):
        evt_pos = event.GetPosition()
        list_pos = control.ScreenToClient(evt_pos)
        return control.HitTest(list_pos)



class PADDING:
    VERTICAL = WxHelper.GetFlags(left=False, right=False)
    HORIZONTAL = WxHelper.GetFlags(top=False, bottom=False)
    ALL = WxHelper.GetFlags()

class ALIGN:
    CENTER = wx.ALIGN_CENTER | wx.EXPAND
    LEFT = wx.ALIGN_LEFT | wx.EXPAND
    RIGHT = wx.ALIGN_RIGHT | wx.EXPAND