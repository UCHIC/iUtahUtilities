import string
import wx
import wx.xrc

CV_ALPHANUMERIC = string.letters + string.digits
CV_WORD = CV_ALPHANUMERIC + '_'
CV_DIGIT_ONLY = string.digits
CV_ALPHA_ONLY = string.letters
CV_DENY_CUSTOM = ''
CV_HOSTNAME = CV_ALPHANUMERIC + '.://&'
CV_USERNAME = CV_ALPHANUMERIC + '_.@'

class CharValidator(wx.PyValidator):
    ''' Validates data as it is entered into the text controls. '''

    #----------------------------------------------------------------------
    def __init__(self, allow, deny=None):
        wx.PyValidator.__init__(self)
        self.allowed = allow if allow is not None else ""
        self.denied = deny if deny is not None else ""
        self.Bind(wx.EVT_CHAR, self.OnChar)

    #----------------------------------------------------------------------
    def Clone(self):
        '''Required Validator method'''
        return CharValidator(self.allowed, self.denied)

    #----------------------------------------------------------------------
    def Validate(self, win):
        return True

    #----------------------------------------------------------------------
    def TransferToWindow(self):
        return True

    #----------------------------------------------------------------------
    def TransferFromWindow(self):
        return True

    #----------------------------------------------------------------------
    def OnChar(self, event):
        keycode = int(event.GetKeyCode())
        if 31 < keycode < 256:
            key = chr(keycode)
            if key in self.denied:
                return
            if key not in self.allowed:
                return
        event.Skip()
