import sys
import os
import logging
import datetime

import pandas as pd


this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)
from odmservices import ServiceManager
from logger import LoggerTool

tool = LoggerTool()
logger = tool.setupLogger(__name__, __name__ + '.log', 'a', logging.DEBUG)

sm = ServiceManager()



def handleConnection(database, location, dump_location):
    #Getting the data
    sm._current_connection={'engine': 'mssql', 'user': 'webapplication', 'password': 'W3bAppl1c4t10n!', 'address': 'iutahdbs.uwrl.usu.edu', 'db': database}
    ss = sm.get_series_service()
    sites = ss.get_all_sites()

    logger.info("Started getting sites for " + database)
    #get current year,
    year = datetime.datetime.now().strftime('%Y')

    #loop through each site
    for site in sites:

        #generate file name
        file_name =  "iUTAH_GAMUT_" + site.code +"_RawData_"+year+".csv"
        file_path = dump_location + file_name
        #logger.info("Started getting values for " + site.code)
        series = ss.get_series_by_site_code(site.code)
        numvar= len(series)
        colcount = 0
        if fileexists(file_path):
             #start date , colcount = call mario function
            logger.info("Updating file " + file_name)
            startdate, colcount = parseCSVData(file_path)

        if not fileexists(file_path) or colcount > numvar :
             #set start date to jan 1 of curr year
            #colcount = 0
            logger.info("Creating a new file " + file_name)
            startdate = datetime.datetime(int(year),01,01,0,0,0)
            colcount = 0
        elif colcount<numvar:
            logger.info("File Incorrect: " + file_name + " variables removed")



            #this line is just for testing, to shorten the amount of test data
            #startdate = datetime.datetime(int(year),11,18,0,0,0)

        #dvs= get data at site since startdate
        dvs = ss.get_all_values_by_site_id_date(site.id, startdate)
        if len(dvs) > 0:
            df=pd.DataFrame([x.list_repr() for x
                             in dvs], columns=dvs[0].get_columns())
            del dvs
            #df.set_index([ "ValueID", 'LocalDateTime', 'UTCOffset', 'DateTimeUTC'])
            df=pd.pivot_table(df, index= ["LocalDateTime", "UTCOffset","DateTimeUTC"], columns = "VariableCode", values = "DataValue")
            #pv=df.pivot(index="LocalDateTime", columns="VariableCode", values="DataValue")


            # if colcount not equal to dvs.colcount ( will match if there is new file or the number of vars have changed)
            if colcount != len(df.columns):
                f=open(file_path,'w')
                #generate header


                file_str = generateHeader(site, location)
                # Getting and organizing all the data
                var_data = VariableData()

                for s in series:
                    var_data.addData(s.variable)
                    var_data.addMethodInfo(s.method.description, s.method.link)

                source= series[0].source
                sourceInfo = SourceInfo()
                sourceInfo.setSourceInfo(source.organization, source.description, source.link,
                                                     source.contact_name, source.phone, source.email, source.citation)
                #print header
                file_str += var_data.printToFile()

                file_str += "#\n"
                file_str += sourceInfo.outputSourceInfo()
                file_str += "#\n"

                #print data and headers to file
                #f.write("text\n\n\n")
                f.write(file_str)
                del file_str
                del sourceInfo
                del source
                del series
                del var_data
                df.to_csv(f)
                f.close()
                logger.info("Finished creating " + "iUTAH_GAMUT_" + site.code +"_RawData_(insertYear)" + " CSV file. ")
            else:
            #   open file for appending
                with open(file_path, 'a') as f:
                    #append values to CSV
                    df.to_csv(f, header=False)
                logger.info("Finished updating " + "iUTAH_GAMUT_" + site.code +"_RawData_(insertYear)" + " CSV file. ")

            #if file is not empty then get the latest value only (make another function)


        else:
            del dvs

       # del text_file


def fileexists(file_path):
    import os
    return os.path.exists(file_path)

def generateHeader(site, location):
    file_str = ""

    file_str = "# ------------------------------------------------------------------------------------------\n"
    file_str += "# WARNING: These are raw and unprocessed data that have not undergone quality control.\n"
    file_str += "# They are provisional and subject to revision. The data are released on the condition \n"
    file_str += "# that neither iUTAH nor any of its participants may be held liable for any damages\n"
    file_str += "# resulting from thier use. The following metadata describe the data in this file:\n"
    file_str += "# ------------------------------------------------------------------------------------------\n"
    file_str += "#\n"
    file_str += "# Site Information\n"
    file_str += "# ----------------------------------\n"
    file_str += "# Network: "+ location + "\n"
    file_str += "# SiteCode: " + str(site.code) + "\n"
    file_str += "# SiteName: " + str(site.name) + "\n"
    file_str += "# Latitude: " + str(site.latitude) + "\n"
    file_str += "# Longitude: " + str(site.longitude) + "\n"
    file_str += "# Elevation_m: " + str(site.elevation_m) +"\n"
    file_str += "# ElevationDatum: " + str(site.vertical_datum) +"\n"
    file_str += "# State: " + str(site.state) +"\n"
    file_str += "# County: " + str(site.county) + "\n"
    file_str += "# Comments: " + str(site.comments) +"\n"
    file_str += "# SiteType: " + str(site.type) + "\n"
    file_str += "#\n"
    file_str += "# Variable and Method Information\n"
    file_str += "# ---------------------------\n"
    return file_str


def outputValues(ss, dvObjects, site, header_str, dump_location):
    timeIndexes = ss.get_all_local_date_times_by_siteid(site.id)
    currentYear = 1900
    #gotta optimize this for loop somehow.

    if len(timeIndexes)>0:
        for time in timeIndexes:
            outputStr = ""
            if time.local_date_time.year != currentYear:
                if currentYear != 1900:
                    text_file.close()
                    logger.info("Finished creating " + "iUTAH_GAMUT_" + site.code +"_RawData_"+ str(currentYear) + " CSV file. ")
                currentYear = time.local_date_time.year
                text_file = open(dump_location + "iUTAH_GAMUT_" + site.code +"_RawData_"+ str(currentYear) + ".csv", "w")
                text_file.write(header_str)

            outputStr += str(time[0]) + ", " + str(time[1]) + ", " + str(time[2]) + ", "
            counter = 0

            for var in dvObjects.varCode:
                var_print = next((dv for dv in dvObjects.dataValues[counter] if dv.local_date_time == time[0]), None)
                if var_print != None:
                    outputStr += str(var_print.data_value) + ", "
                    dvObjects.dataValues[counter].remove(var_print)
                    #print len(dvObjects.dataValues[counter])
                else:
                    outputStr += ", "
                    #print "Not Found!"


                counter += 1

            ouputStr = outputStr[:-2]
            outputStr += "\n"

            text_file.write(outputStr)

        text_file.close()



def parseCSVData(filePath):
    csvFile = open(filePath, "r")
    lastLine = getLastLine(csvFile)
    csvFile.close()
    return getDateAndNumCols(lastLine)

def getLastLine(targetFile):
    firstCharSeek = ''
    readPosition = -3
    prevLine = result = ""
    while firstCharSeek != '\n':
        targetFile.seek(readPosition, os.SEEK_END)
        readPosition -= 1
        result = prevLine #last line was being deleted. So I saved a temp to keep it
        prevLine = targetFile.readline()
        firstCharSeek = prevLine[0]
    return result

def getDateAndNumCols(lastLine):
    strList = lastLine.split(",")
    dateTime = datetime.datetime.strptime(strList.pop(0), '%Y-%m-%d %H:%M:%S')
    utc=strList.pop(0)
    utcdate=strList.pop(0)
    '''
    count = 0
    for value in strList:
        isValueCorrect = strList.index(value) > 0 and value != " \n"# and value != " ": #I guess we are considering all columns even if there are no values.
        if isValueCorrect:
            count += 1
    '''
    count = len (strList)
    return dateTime, count


# Test case for parseCSVData and related functions
#dateAndColsObj = parseCSVData("C:\\iUTAH_GAMUT_PR_BD_C_RawData_2013.csv")
#print dateAndColsObj.localDateTime
#print dateAndColsObj.numCols

def dataParser( dump_loc):

    logger.info("\n========================================================\n")
    #logan database is loaded here
    logger.info("Started creating files.")
    handleConnection('iUTAH_Logan_OD', 'Logan', dump_loc)

    #provo database is loaded here
    handleConnection('iUTAH_Provo_OD', 'Provo', dump_loc)

    #red butte creek database is loaded here
    handleConnection('iUTAH_RedButte_OD', 'RedButte', dump_loc)

    logger.info("Finished Program. ")
    logger.info("\n========================================================\n")







class SourceInfo:
    def __init__(self):
        self.organization = ""
        self.sourceDescription = ""
        self.sourceLink = ""
        self.contactName = ""
        self.phone = ""
        self.email = ""
        self.citation = ""

    def setSourceInfo(self, org, srcDesc, srcLnk, cntctName, phn, email, citn):
        self.organization = org
        self.sourceDescription = srcDesc
        self.sourceLink = srcLnk
        self.contactName = cntctName
        self.phone = phn
        self.email = email
        self.citation = citn

    def outputSourceInfo(self):
        outputStr = "# Source Information\n# ------------------\n"
        outputStr += self.sourceOutHelper("Organization", self.organization)
        outputStr += self.sourceOutHelper("SourceDescription", self.sourceDescription)
        outputStr += self.sourceOutHelper("SourceLink", self.sourceLink)
        outputStr += self.sourceOutHelper("ContactName", self.contactName)
        outputStr += self.sourceOutHelper("Phone", self.phone)
        outputStr += self.sourceOutHelper("Email", self.email)
        outputStr += self.sourceOutHelper("Citation", self.citation)
        return outputStr

    def sourceOutHelper(self, title, value):
        return "# " + title + ": " + value + "\n"

class VariableData:
    def __init__(self):
        self.varCode = []
        self.varName = []
        self.valueType = []
        self.dataType = []
        self.gralCategory = []
        self.sampleMedium = []
        self.varUnitsName = []
        self.varUnitsType = []
        self.varUnitsAbbr = []
        self.noDV = []
        self.timeSupport = []
        self.timeSupportUnitsAbbr = []
        self.timeSupportUnitsName = []
        self.timeSupportUnitsType = []
        self.methodDescrition = []
        self.methodLink = []

        self.dataValues = [] 

    def addDataValue(self, dataV):
        self.dataValues[len(self.varCode) - 1].append(dataV)

    def addData(self, var):

        self.varCode.append(var.code)
        self.varName.append(var.name)
        self.valueType.append(var.value_type)
        self.dataType.append(var.data_type)
        self.gralCategory.append(var.general_category)
        self.sampleMedium.append(var.sample_medium)
        self.varUnitsName.append(var.variable_unit.name)
        self.varUnitsType.append(var.variable_unit.type)
        self.varUnitsAbbr.append(var.variable_unit.abbreviation)
        self.noDV.append(var.no_data_value)
        self.timeSupport.append(var.time_support)
        self.timeSupportUnitsAbbr.append(var.time_unit.abbreviation)
        self.timeSupportUnitsName.append(var.time_unit.name)
        self.timeSupportUnitsType.append(var.time_unit.type)

        self.dataValues.append([])

    def addMethodInfo(self, methoddescription, methodlink):
        self.methodDescrition.append(methoddescription)
        self.methodLink.append(methodlink)
        
        

    def printToFile(self):
        formatted = ""
        for x in range(0, len(self.varCode)):
            formatted += "# "
            formatted += self.formatHelper("VariableCode", self.varCode[x])
            formatted += self.formatHelper("VariableName", self.varName[x])
            formatted += self.formatHelper("ValueType", self.valueType[x])
            formatted += self.formatHelper("DataType", self.dataType[x])
            formatted += self.formatHelper("GeneralCategory", self.gralCategory[x])
            formatted += self.formatHelper("SampleMedium", self.sampleMedium[x])
            formatted += self.formatHelper("VariableUnitsName", self.varUnitsName[x])
            formatted += self.formatHelper("VariableUnitsType", self.varUnitsAbbr[x])
            formatted += self.formatHelper("VariableUnitsAbbreviation", self.varUnitsAbbr[x])
            formatted += self.formatHelper("NoDataValue", self.noDV[x])
            formatted += self.formatHelper("TimeSupport", self.timeSupport[x])
            formatted += self.formatHelper("TimeSupportUnitsAbbreviation", self.timeSupportUnitsAbbr[x])
            formatted += self.formatHelper("TimeSupportUnitsName", self.timeSupportUnitsName[x])
            formatted += self.formatHelper("TimeSupportUnitsType", self.timeSupportUnitsType[x])
            formatted += self.formatHelper("MethodDescription", self.methodDescrition[x])
            formatted += self.formatHelper("MethodLink", self.methodLink[x])
            formatted = formatted[:-2]
            formatted += "\n"
            
        return formatted

    def formatHelper(self, title, var):
        formatted = title+": "+ str(var) + " | "
        return formatted 
            
                    
'''

#update all of the files
dataParser(dump_loc = "C:\\Users\\Stephanie\\Desktop\\csvsites\\Srfiles\\")
'''