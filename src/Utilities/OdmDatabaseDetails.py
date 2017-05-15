

class DatasetRule:
    def __init__(self):
        self.name = ""



class H2O2:
    def __init__(self):
        self.name = "H2O Operation"
        self.dataset_rules = None
        self.hydroshare_rules = None



"""

Rules have:
    Names
    File-delimiters




BOOM. Dataset generation has rules, but HydroShare has pairs.

HydroShare determines pairs based on site codes.
    We can either go explicit designation, or rule-based designation.
    
    I wanna go rule-based.
        The rule could be, this 

Currently filtering down the resources we know we want to upload to,
    then from there anticipating one site per resource.




Each file will have to go to a specific resource.

We have some options:

    1. We can have two types of rules
        a. Regex-kinda rule - look for resource names that match what we expect
        b. Manual dataset-target designation. "All new resources" would populate rules
        c. 


"""