USE [DatabaseName]
GO
/****** Object:  StoredProcedure [dbo].[spCheckNANs]    Script Date: 1/21/2015 11:42:18 AM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
---------- =============================================
-- Author:		Amber S Jones
-- Create date: 1-21-2014
-- Modified:    2-3-2014
-- Description:	Performs a count of NAN values to see whether there are 
-- more than an acceptable count.
-- =============================================

ALTER PROCEDURE [dbo].[spCheckNANs] 
@NANCountThreshold AS VARCHAR(20) = 10

AS

IF EXISTS (SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, COUNT(DataValue) AS DataCount 
FROM [DatabaseName].[dbo].[DataValues] AS dv
JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
WHERE dv.VariableID NOT IN (11) AND DataValue = -9999 AND LocalDateTime >= DATEADD(hour, -24, SYSDATETIME())
GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode
HAVING COUNT(DataValue) > 10)

BEGIN

DECLARE @qry VARCHAR(700)
SET @qry = 'SELECT dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode, COUNT(DataValue) AS DataCount 
				FROM [DatabaseName].[dbo].[DataValues] AS dv
				JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
				JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
				WHERE dv.VariableID NOT IN (11) AND DataValue = -9999 AND LocalDateTime >= DATEADD(hour, -24, SYSDATETIME())
				GROUP BY dv.SiteID, s.SiteCode, dv.VariableID, v.VariableCode
				HAVING COUNT(DataValue) > ' + @NANCountThreshold

	SET NOCOUNT ON

	EXEC msdb.dbo.sp_send_dbmail
	@profile_name = 'USU Email',
	@from_address = 'data.alerts@usu.edu',
	@recipients = 'recipient@usu.edu; technician@usu.edu',
	@subject = 'Data Warning',
	@body = 'The following results are reporting NAN or -9999.',
	@query = @qry ;

END






