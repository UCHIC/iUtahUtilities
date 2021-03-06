USE [DatabaseName]
GO
/****** Object:  StoredProcedure [dbo].[spCheckLatest]    Script Date: 1/21/2015 11:42:11 AM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
---------- =============================================
-- Author:		Amber S Jones
-- Create date: 1-22-2014
-- Modified:    2-3-2014
-- Description:	Checks the datetime of the most recent value
-- and sends an email if it is outside the defined time frame.
-- Data series are only checked if they have been collected within 
-- the past 48 hours and then the email is sent if the data has not
-- been reported in the past 24 hours. This ensures that the alert
-- is not generated for inactive data series.
-- =============================================

ALTER PROCEDURE [dbo].[spCheckLatest] 

AS

IF EXISTS (SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, MAX(LocalDateTime) AS LastDateTime 
FROM [DatabaseName].[dbo].[DataValues] AS dv
JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
WHERE LocalDateTime >= DATEADD(hour, -48, SYSDATETIME())
GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode
HAVING MAX(LocalDateTime) < DATEADD(hour, -24, SYSDATETIME()))

BEGIN

DECLARE @qry VARCHAR(1000)
SET @qry = 'SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, MAX(LocalDateTime) AS LastDateTime 
			FROM [DatabaseName].[dbo].[DataValues] AS dv
			JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
			JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
			WHERE LocalDateTime >= DATEADD(hour, -48, SYSDATETIME())
			GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode
			HAVING MAX(LocalDateTime) < DATEADD(hour, -24, SYSDATETIME())'

	SET NOCOUNT ON

	EXEC msdb.dbo.sp_send_dbmail
	@profile_name = 'USU Email',
	@from_address = 'data.alerts@usu.edu',
	@recipients = 'recipient@usu.edu; technician@usu.edu',
	@subject = 'Data Warning',
	@body = 'Data has not updated for the following data series.',
	@query = @qry ;

END





