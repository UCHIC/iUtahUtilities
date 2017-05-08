

class H20State:
    def __init__(self):
        self.hydroshare_accounts = {}
        self.odm_connections = {}


class OdmDatabaseDetails:
    def __init__(self):
        self.name = ""
        self.engine = ""
        self.user = ""
        self.password = ""
        self.address = ""
        self.database = ""

    def ToDict(self):
        return {'engine': self.engine, 'user': self.user, 'password': self.password, 'address': self.address,
                'db': self.database}

class HydroShareAccountDetails:
    def __init__(self):
        self.name = ""
        self.username = ""
        self.password = ""
        self.client_id = ""
        self.client_secret = ""

