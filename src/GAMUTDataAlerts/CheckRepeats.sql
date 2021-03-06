USE [DatabaseName]
GO
/****** Object:  StoredProcedure [dbo].[spCheckRepeats]    Script Date: 1/21/2015 12:54:30 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
---------- =============================================
-- Author:		Amber S Jones
-- Create date: 1-21-2014
-- Modified:    10-28-2014
-- Description:	Examines a sequence of values, determines whether any are repeated, and  
-- sends an email if the count exceeds the acceptable threshold. Certain variables and -9999 values excluded.
-- =============================================

ALTER PROCEDURE [dbo].[spCheckRepeats]
@RepeatThreshold VARCHAR(20) = 15

AS

WITH Sequences AS (
SELECT dv.SiteID, CAST(s.SiteCode AS nvarchar(12)) AS SiteCode, dv.VariableID, CAST(v.VariableCode AS nvarchar(20)) AS VariableCode, LocalDateTime, DataValue,
	ROW_NUMBER() OVER (PARTITION BY dv.SiteID, dv.VariableID, DataValue ORDER BY LocalDateTime) AS RNO,
    ROW_NUMBER() OVER (ORDER BY dv.SiteID, dv.VariableID, LocalDateTime) AS RNE
  FROM [DatabaseName].[dbo].[DataValues] AS dv
  JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
  JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
  --exclude several variables that typically repeat
  WHERE LocalDateTime >= DATEADD(hour, -24, SYSDATETIME()) AND dv.VariableID NOT IN (10, 22, 54, 55, 56, 72, 75, 76, 80, 81, 82, 90, 91, 94, 95, 96, 97, 98, 105, 106, 107, 109, 110, 111, 112, 113, 114, 115, 116, 117, 121)
  AND DataValue NOT IN (-9999)) 
SELECT seq.SiteID, seq.SiteCode, seq.VariableID, seq.VariableCode, 
	CAST(seq.DataValue AS numeric(10,2)) AS DataValue,
	CONVERT(char(16), MIN(seq.LocalDateTime), 120) AS [Start],
	CONVERT(char(16), MAX(seq.LocalDateTime), 120) AS [End],
	COUNT(*) AS ValueCount
  FROM Sequences AS seq
  --exclude SoilCond and Radiation variables when those variables=0
  WHERE (seq.VariableID IN (13, 14, 15, 16, 17, 18, 19, 21, 24, 25, 33, 37, 41, 45, 49) AND seq.DataValue <> 0) OR seq.VariableID NOT IN (13, 14, 15, 16, 17, 18, 19, 21, 24, 25, 33, 37, 41, 45, 49)
  GROUP BY seq.SiteID, seq.SiteCode, seq.VariableID, seq.VariableCode, seq.DataValue, seq.RNE - seq.RNO
  HAVING COUNT(*) > 15

BEGIN

DECLARE @qry varchar(2000)
SET @qry = 'WITH Sequences AS (
SELECT dv.SiteID, CAST(s.SiteCode AS nvarchar(12)) AS SiteCode, dv.VariableID, CAST(v.VariableCode AS nvarchar(20)) AS VariableCode, LocalDateTime, DataValue,
	ROW_NUMBER() OVER (PARTITION BY dv.SiteID, dv.VariableID, DataValue ORDER BY LocalDateTime) AS RNO,
    ROW_NUMBER() OVER (ORDER BY dv.SiteID, dv.VariableID, LocalDateTime) AS RNE
  FROM [DatabaseName].[dbo].[DataValues] AS dv
  JOIN [DatabaseName].[dbo].[Sites] AS s ON dv.SiteID = s.SiteID
  JOIN [DatabaseName].[dbo].[Variables] AS v ON dv.VariableID = v.VariableID
  --exclude several variables that typically repeat
  WHERE LocalDateTime >= DATEADD(hour, -24, SYSDATETIME()) AND dv.VariableID NOT IN (10, 22, 54, 55, 56, 72, 75, 76, 80, 81, 82, 90, 91, 94, 95, 96, 97, 98, 105, 106, 107, 109, 110, 111, 112, 113, 114, 115, 116, 117, 121)
  AND DataValue NOT IN (-9999)) 
SELECT seq.SiteID, seq.SiteCode, seq.VariableID, seq.VariableCode, 
	CAST(seq.DataValue AS numeric(10,2)) AS DataValue,
	CONVERT(char(16), MIN(seq.LocalDateTime), 120) AS [Start],
	CONVERT(char(16), MAX(seq.LocalDateTime), 120) AS [End],
	COUNT(*) AS ValueCount
  FROM Sequences AS seq
  --exclude SoilCond and Radiation variables when those variables=0
  WHERE (seq.VariableID IN (13, 14, 15, 16, 17, 18, 19, 21, 24, 25, 33, 37, 41, 45, 49) AND seq.DataValue <> 0) OR seq.VariableID NOT IN (13, 14, 15, 16, 17, 18, 19, 21, 24, 25, 33, 37, 41, 45, 49)
  GROUP BY seq.SiteID, seq.SiteCode, seq.VariableID, seq.VariableCode, seq.DataValue, seq.RNE - seq.RNO
  HAVING COUNT(*) >' + @RepeatThreshold
	SET NOCOUNT ON

	EXEC msdb.dbo.sp_send_dbmail
	@profile_name = 'USU Email',
	@from_address = 'data.alerts@usu.edu',
	@recipients = 'recipient@usu.edu; technician@usu.edu',
	@subject = 'Data Warning',
	@body = 'The following results are have repeated values in the past day.',
	@query = @qry;

END






