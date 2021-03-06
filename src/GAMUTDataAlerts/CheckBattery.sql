USE [DatabaseName]
GO
/****** Object:  StoredProcedure [dbo].[spCheckBattery]    Script Date: 1/21/2015 11:41:57 AM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
---------- =============================================
-- Author:		Amber S Jones
-- Create date: 11-26-2013
-- Modified:    2-3-2014
-- Description:	Checks the battery voltage and sends
-- an email if it is outside the predefined range.
-- =============================================

ALTER PROCEDURE [dbo].[spCheckBattery] 
@VoltageThreshold VARCHAR(20) = 12

AS

IF EXISTS (SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, COUNT(DataValue) AS DataCount 
FROM [DatabaseName].[dbo].[DataValues] AS dv
JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
WHERE dv.VariableID = 51 AND DataValue < @VoltageThreshold AND LocalDateTime >= DATEADD(hour, -24, SYSDATETIME())
GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode)


BEGIN 

DECLARE @qry VARCHAR(500)
SET @qry = 'SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, COUNT(DataValue) AS DataCount 
			FROM [DatabaseName].[dbo].[DataValues] AS dv
			JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
			JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
			WHERE dv.VariableID = 51 AND DataValue < ' + @VoltageThreshold + ' AND LocalDateTime >= DATEADD(hour, -24, SYSDATETIME())
			GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode'

	SET NOCOUNT ON

	EXEC msdb.dbo.sp_send_dbmail
	@profile_name = 'USU Email',
	@from_address = 'data.alerts@usu.edu',
	@recipients = 'recipient@usu.edu; technician@usu.edu',
	@subject = 'Data Warning',
	@body = 'The following results are outside the range defined for acceptable battery voltage.',
	@query = @qry ;

END






