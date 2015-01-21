This folder contains the source code for the Microsoft SQL Server Stored Procedures that perform automated quality assurance and data alerts for continuous sensor data stored within a CUAHSI ODM database. These stored procedures should be associated with the database on which they are to run. They can be scheduled to run regularly to check the data and send alerts to technicans. All of these procedures are based on data patterns over the past 24 hours, so the schedule is run and alerts are generated on a daily basis. 

##Setting Up Database Mail
In order to send emails through SQL Server, Database Mail needs to be setup, which can be done with the below steps:  
1. In SQL Server Management Studio, under ‘Management’, right click on Database Mail, and select ‘Configure Database Mail’.  
2. Select ‘Set Up Database Mail’.  
3. Create a Profile Name and Description.   
4. Give the outgoing email address, display name, and reply email address.  
5. Enter the server name, port number, and authentication (if required) as applies to your email server.  
6. Finish the setup.  
7. Right click Database Mail to ‘Send Test Email’.  

##Scheduling the Alerts
SQL Server uses 'Jobs' to schedule tasks. To schedule the data alerts as an automated job, follow these steps:  
1. Ensure that that the SQL Server Agent is started and running.  
2. In SQL Server Management Studio, under 'SQL Server Agent', right click on 'Jobs', and select ‘Create New Job’.  
3. Give the job a Name and Description.  
4. Go to the ‘Steps’ page and add each stored procedure as a step:  
  1. Click ‘New’.  
  2. Give the step a descriptive name, select ‘Transact-SQL script T-SQL’, and select the appropriate database.  
  3. In the ‘Command’ box, type: EXEC [dbo].[NameofStoredProcedure]  
  4. In the ‘Advanced’ tab, select the ‘On success action’ and the ‘On failure action’ - e.g., Go to the next step.  
5. Go to the ‘Schedules’ page and create the schedule for the job to run:  
  1. Click ‘New’.  
  2. Give the schedule a descriptive name, and select ‘Recurring’.  
  3. Set the Frequency, Timing, and Duration for which you want the job to run.  
6. Go to the ‘Notifications’ page and set an email if you want to receive a notification for the job succeeding or failing. (NOTE: An email address must be set up as an 'Operator' under SQL Server Agent to be notified.)  
7. To test the job, right click on the job name and select ‘Start Job at Step’.  
8. To view the job history, right click on the job name and select ‘View History’. See a record of each time the job was executed, the steps that were performed, whether the step was successful, any errors, and whether an email was sent for each step.

##Check Battery
The Check Battery procedure checks whether battery voltage at a site has dropped below a certain threshold within the past 24 hours. If so, an email alert is generated. The threshold is defined by the @VoltageThreshold parameter and is set in the procedure with this command: @VoltageThreshold VARCHAR(20) = 12. For iUTAH, the threshold is 12 V. The VariableID should be set as the battery voltage VariableID in the database of interest. For the iUTAH databases, VariableID = 51.

##Check Latest
The Check Latest procedure verifies whether data are updating. If not, an email alert is generated. To check updating, the DateTime of the most recent value is examined to see if it is within the past 24 hours. To ensure that the alert is not generated for inactive data series,  Tdata series are only checked if they have been collected within the past 48 hours and then the email is sent if the data has not been reported in the past 24 hours. As a result, alerts will only be sent for a data series once. If the data series does not update, new alerts will not be generated.

##Check NANs
The Check NAN procedure performs a count of 'No Data' values for each data series in the past 24 hours. If the count is greater than a certain threshold, an email alert is generated. The threshold is defined by the @NANCountThreshold parameter, which is set in the procedure with this command: @NANCountThreshold AS VARCHAR(20) = 10. For iUTAH, the threshold is a count of 10. Note that the 'No Data' value for the iUTAH databases is -9999, so this is the value that the procedure is counting. When a datalogger records 'NAN' (not a number), these records are imported into the database and assigned a value of '-9999'.

##Check Repeats
The Check Repeats procedure looks for the persistence of values in a data series. To do so, it examines the sequence of records in a data series and determines if any were repeated over the past 24 hours. If so, and if the number of repeated values exceeds the acceptable threshold, an email alert is generated. The threshold is defined by the @RepeatThreshold parameter, which is set in the procedure with this command: @RepeatThreshold VARCHAR(20) = 15. For iUTAH, the threshold is a count of 15. This may still generate some false positives, but seems suitable for our desired level of Quality Assurance. Note that -9999 values were excluded as well as variables that commonly repeat or for which the procedure is of little interest. This is done via the dv.VariableID NOT IN() statement.

##Create Your Own Procedure
To create a procedure with your own specific conditions, use the IF EXISTS() statement to set the condition for wether the database mail procedure will be called. The database mail procedure should be called within the stored procedure as shown below. Additional parameters may be used. If it is desired to show the results of the procedure in the email (i.e., which series triggered the alert), the query needs to be pasted into the @query field.

    BEGIN   
  	  EXEC msdb.dbo.sp_send_dbmail  
  	  @profile_name = 'ProfileName created on Database Mail',  
  	  @from_address = 'email address alias',  
  	  @recipients = 'recipient email addresses separated by semicolon',  
  	  @subject = 'Subject Line',  
  	  @body = 'Message for the body',  
  	  @query = ‘Query for which results should appear in the body of the email’ ;  
    END
