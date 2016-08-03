import sys
import os
import logging
import datetime

import pandas as pd

this_file = os.path.realpath(__file__)
directory = os.path.dirname(os.path.dirname(this_file))

sys.path.insert(0, directory)
from odmservices import ServiceManager

formatString = '%s  %s: %s'
service_manager = ServiceManager()

issues = []


class CsvLocalDataset:
    def __init__(self, dump_location, location, site, year):
        self.site = site
        self.location = location
        self.csv_filename = 'iUTAH_GAMUT_{site}_RawData_{yr}.csv'.format(site=site.code, yr=year)
        self.csv_filepath = "{path}{name}".format(path=dump_location, name=self.csv_filename)

        self.year = year
        self.start_date = datetime.datetime(int(year), 01, 01, 0, 0, 0)
        self.end_date = datetime.datetime(int(year), 12, 31, 23, 55, 59)
        self.column_count = 0

    def createFile(self, filepath=None):
        """

        :param file_path:
        :type file_path:
        :return:
        :rtype:
        """
        if filepath is None:
            filepath = self.csv_filepath

        try:
            print(filepath)
            if False and os.path.exists(filepath):
                # start date , colcount = call mario function
                print formatString % (datetime.datetime.now(), "handleConnection", "Updating " + filepath)
                self.start_date, self.column_count = self.parseCSVData(filepath)
                file_out = open(filepath, 'a')
            else:  # or colcount != numvar:
                print formatString % (datetime.datetime.now(), "handleConnection", "Creating a new file " + filepath)
                file_out = open(filepath, 'w')
            return file_out
        except Exception as e:
            print('Issue encountered while creating a new file: {}'.format(e))
            return None

    def writeToFile(self, series_service, series_list, filepath=None, constrain_to_year=True):
        print('Processing site {} with {} series items'.format(self.site.code, len(series_list)))
        issue_list = []
        try:
            file_out = self.createFile(filepath)
            if file_out is None:
                issue_list.append('Unable to create file for output')
                return issue_list

            numvar = len(series_list)
            colcount = 0

            # if not fileexists(file_path) or colcount > numvar :

            # dvs= get data at site since startdate
            print("Attempting to fetch data for site {}".format(self.site.id))
            dvs = series_service.get_all_values_by_site_id_date(self.site.id, self.start_date)

            print('DVS count: {}'.format(len(dvs)))
            # del dvs
            if len(dvs) > 0:
                # df = pd.DataFrame([x.list_repr() for x
            #                        in dvs], columns=dvs[0].get_columns())
            #     del dvs
                dvs.set_index([ "ValueID", 'LocalDateTime', 'UTCOffset', 'DateTimeUTC'])
                df = pd.pivot_table(dvs, index=["LocalDateTime", "UTCOffset", "DateTimeUTC"], columns="VariableCode",
                                    values="DataValue")
                # pv=df.pivot(index="LocalDateTime", columns="VariableCode", values="DataValue")
                collist = len(df.columns)
            #
            #     # if colcount not equal to dvs.colcount  colcount number of columns in the file
            #     # collist number of columns from the database
            #     # ( will match if there is new file or the number of vars have changed)
            #     if colcount != collist:
            #         # f = open(file_path, 'w')
            #         # generate header
            #         file_str = self.generateHeader()
            #         # Getting and organizing all the data
            #         var_data = VariableData()
            #
            #         for s in series:
            #             var_data.addData(s.variable)
            #             var_data.addMethodInfo(s.method.description, s.method.link)
            #
            #         source = series[0].source
            #         sourceInfo = SourceInfo()
            #         sourceInfo.setSourceInfo(source.organization, source.description, source.link,
            #                                  source.contact_name, source.phone, source.email, source.citation)
            #         # print header
            #         file_str += var_data.printToFile()
            #
            #         file_str += "#\n"
            #         file_str += sourceInfo.outputSourceInfo()
            #         file_str += "#\n"
            #
            #         # print data and headers to file
            #         # f.write("text\n\n\n")
            #         file_out.write(file_str)
            #         del file_str
            #         del sourceInfo
            #         del source
            #         # del series
            #         del var_data
            #         df.to_csv(file_out)
            #         file_out.close()
            #         # print FORMAT_STRING %(datetime.datetime.now(), "handleConnection",  "Finished creating " +
            #         # file_name + " CSV file. ")
            #     else:
            #         #   open file for appending
            #         # with open(file_path, 'a') as f:
            #             # append values to CSV
            #         df.to_csv(file_out, header=False)
            #             # print FORMAT_STRING %(datetime.datetime.now(), "handleConnection",  "Finished updating "
            #             # +file_name + " CSV file. ")
            #
            #             # if file is not empty then get the latest value only (make another function)
            # else:
            #     print("Unable to retrieve data value set for site {} with name of {}".format(self.site.code, self.site.name))
            #     del dvs

            del dvs
            # del text_file
        except Exception as e:
            msg = " SiteName: %s, year: %s, Error : %s" % (self.site, self.year, e)
            print formatString % (datetime.datetime.now(), "handleConnection", msg)
            issue_list.append(msg)

    def generateHeader(self):
        """
        :return: Returns a string to be inserted as the CSV file's header
        :rtype: str
        """
        file_str = "# ------------------------------------------------------------------------------------------\n"
        file_str += "# WARNING: These are raw and unprocessed data that have not undergone quality control.\n"
        file_str += "# They are provisional and subject to revision. The data are released on the condition \n"
        file_str += "# that neither iUTAH nor any of its participants may be held liable for any damages\n"
        file_str += "# resulting from their use. The following metadata describe the data in this file:\n"
        file_str += "# ------------------------------------------------------------------------------------------\n"
        file_str += "#\n"
        file_str += "# Site Information\n"
        file_str += "# ----------------------------------\n"
        file_str += "# Network: " + self.location + "\n"
        file_str += "# SiteCode: " + str(self.site.code) + "\n"
        file_str += "# SiteName: " + str(self.site.name) + "\n"
        file_str += "# Latitude: " + str(self.site.latitude) + "\n"
        file_str += "# Longitude: " + str(self.site.longitude) + "\n"
        file_str += "# Elevation_m: " + str(self.site.elevation_m) + "\n"
        file_str += "# ElevationDatum: " + str(self.site.vertical_datum) + "\n"
        file_str += "# State: " + str(self.site.state) + "\n"
        file_str += "# County: " + str(self.site.county) + "\n"
        file_str += "# Comments: " + str(self.site.comments) + "\n"
        file_str += "# SiteType: " + str(self.site.type) + "\n"
        file_str += "#\n"
        file_str += "# Variable and Method Information\n"
        file_str += "# ---------------------------\n"
        return file_str

    def parseCSVData(self, filePath):
        try:
            csvFile = open(filePath, "r")
            lastLine = self.getLastLine(csvFile)
            csvFile.close()
            return self.getDateAndNumCols(lastLine)
        except Exception as e:
            print('Exception encountered while attempting to parse the CSV file "{}":\n{}'.format(filePath, e))
            return 0, 0

    def getLastLine(self, targetFile):
        firstCharSeek = ''
        readPosition = -3
        prevLine = result = ""
        while firstCharSeek != '\n':
            targetFile.seek(readPosition, os.SEEK_END)
            readPosition -= 1
            result = prevLine  # last line was being deleted. So I saved a temp to keep it
            prevLine = targetFile.readline()
            firstCharSeek = prevLine[0]
        return result

    def getDateAndNumCols(self, lastLine):
        strList = lastLine.split(",")
        dateTime = datetime.datetime.strptime(strList.pop(0), '%Y-%m-%d %H:%M:%S')
        # utc = strList.pop(0)
        # utcdate = strList.pop(0)
        '''
        count = 0
        for value in strList:
            isValueCorrect = strList.index(value) > 0 and value != " \n"# and value != " ": #I guess we are considering
            all columns even if there are no values.
            if isValueCorrect:
                count += 1
        '''
        count = len(strList)
        return dateTime, count


def handleConnection(database, location, dump_location, year):
    print('Started getting sites for {} at {}'.format(database, location))
    issue_list = []
    # Getting the data
    service_manager._current_connection = {'engine': 'mssql', 'user': 'webapplication', 'password': 'W3bAppl1c4t10n!',
                                           'address': 'iutahdbs.uwrl.usu.edu', 'db': database}
    series_service = service_manager.get_series_service()
    all_sites = series_service.get_all_sites()

    for site in all_sites:
        # generate file name
        local_dataset = CsvLocalDataset(dump_location, location, site, year)
        all_series_list = series_service.get_series_by_site(local_dataset.site.id)
        series_in_range = []
        for series_item in all_series_list:
            start_year = int(series_item.begin_date_time.strftime("%Y"))
            end_year = int(series_item.end_date_time.strftime("%Y"))
            is_in_range = True if start_year <= int(year) <= end_year else False
            if series_item.quality_control_level_id != 0 or not is_in_range:
                continue
            # print('The series {} is within the range'.format(series_item))
            series_in_range.append(series_item)
        if len(series_in_range) > 0:
            local_dataset.writeToFile(series_service, series_in_range)
    return issue_list


def outputValues(ss, dvObjects, site, header_str, dump_location):
    timeIndexes = ss.get_all_local_date_times_by_siteid(site.id)
    currentYear = 1900
    # gotta optimize this for loop somehow.

    if len(timeIndexes) > 0:
        for time in timeIndexes:
            outputStr = ""
            if time.local_date_time.year != currentYear:
                if currentYear != 1900:
                    file_name = "iUTAH_GAMUT_{site}_RawData_{yr}.csv".format(site=site.code, yr=currentYear)
                    text_file.close()
                    print "{} outputValues: Finished creating {}".format(datetime.datetime.now, file_name)
                currentYear = time.local_date_time.year
                text_file = open(dump_location + file_name, "w")
                text_file.write(header_str)

            outputStr += str(time[0]) + ", " + str(time[1]) + ", " + str(time[2]) + ", "
            counter = 0

            for var in dvObjects.varCode:
                var_print = next((dv for dv in dvObjects.dataValues[counter] if dv.local_date_time == time[0]), None)
                if var_print != None:
                    outputStr += str(var_print.data_value) + ", "
                    dvObjects.dataValues[counter].remove(var_print)
                    # print len(dvObjects.dataValues[counter])
                else:
                    outputStr += ", "
                    # print "Not Found!"

                counter += 1

            ouputStr = outputStr[:-2]
            outputStr += "\n"

            text_file.write(outputStr)

        text_file.close()


# Test case for parseCSVData and related functions
# dateAndColsObj = parseCSVData("C:\\iUTAH_GAMUT_PR_BD_C_RawData_2013.csv")
# print dateAndColsObj.localDateTime
# print dateAndColsObj.numCols

def dataParser(dump_loc, year):
    issues = []
    print("\n========================================================\n")
    # logan database is loaded here
    print("Started creating files.")
    issues.append(handleConnection('iUTAH_Logan_OD', 'Logan', dump_loc, year))

    # provo database is loaded here
    issues.append(handleConnection('iUTAH_Provo_OD', 'Provo', dump_loc, year))

    # red butte creek database is loaded here
    issues.append(handleConnection('iUTAH_RedButte_OD', 'RedButte', dump_loc, year))

    print("Finished Program. ")
    print("\n========================================================\n")
    return issues


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
        formatted = title + ": " + str(var) + " | "
        return formatted
