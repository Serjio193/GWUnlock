@echo off
set "SCRIPT_DIR=%~dp0"
for %%D in ("%SCRIPT_DIR%..") do set "TOOL_ROOT=%%~fD"
set "UPSTREAM=%TOOL_ROOT%\upstream"
set "LOG_DIR=%UPSTREAM%\logs"
set "BACKUP_DIR=%UPSTREAM%\backups"
set "MARKER_DIR=%UPSTREAM%\markers"
if defined GW_SERVICE_BACKUP_DIR set "BACKUP_DIR=%GW_SERVICE_BACKUP_DIR%"
if defined GW_SERVICE_MARKER_DIR set "MARKER_DIR=%GW_SERVICE_MARKER_DIR%"
set "BACKUPS=backups"
set "MARKERS=markers"
if defined GW_SERVICE_BACKUP_DIR set "BACKUPS=%GW_SERVICE_BACKUP_DIR%"
if defined GW_SERVICE_MARKER_DIR set "MARKERS=%GW_SERVICE_MARKER_DIR%"
set "BACKUPS_TCL=%BACKUPS:\=/%"
set "ADAPTER=%~1"
set "TARGET=%~2"

if not defined ADAPTER set "ADAPTER=%GW_SERVICE_ADAPTER%"
if not defined TARGET set "TARGET=%GW_SERVICE_TARGET%"
if not defined ADAPTER set "ADAPTER=auto"
if not defined TARGET set "TARGET=mario"
if /i "%ADAPTER%"=="auto" (
  for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "$d=Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.InstanceId -match 'VID_0483|VID_1366|VID_0D28' -or $_.FriendlyName -match 'ST-Link|STLink|J-Link|CMSIS' } | Select-Object -First 1; if ($d.InstanceId -match 'VID_1366' -or $d.FriendlyName -match 'J-Link') { 'jlink' } elseif ($d.InstanceId -match 'VID_0D28' -or $d.FriendlyName -match 'CMSIS') { 'cmsis-dap' } else { 'stlink' }"`) do set "ADAPTER=%%A"
)
if not defined OPENOCD_ADAPTER_SPEED set "OPENOCD_ADAPTER_SPEED=8000"
if not defined LARGE_FLASH set "LARGE_FLASH=1"
set /a GNW_FREQUENCY=%OPENOCD_ADAPTER_SPEED% * 1000

if /i "%TARGET%"=="mario" (
  set "SPIFLASH_SKIP_16=0"
  set "SPIFLASH_COUNT_16=65024"
  set "FLASH_OFFSET=0"
  set "ITCM_OFFSET=0x00"
  set "ITCM_LENGTH=1300"
  set "ITCM_SHA1=ca71a54c0a22cca5c6ee129faee9f99f3a346ca0"
  set "SPI_SHA1=eea70bb171afece163fb4b293c5364ddb90637ae"
  set "INTERNAL_SHA1=efa04c387ad7b40549e15799b471a6e1cd234c76"
) else if /i "%TARGET%"=="zelda" (
  set "SPIFLASH_SKIP_16=8192"
  set "SPIFLASH_COUNT_16=197962"
  set "FLASH_OFFSET=3195816"
  set "ITCM_OFFSET=0x20"
  set "ITCM_LENGTH=1300"
  set "ITCM_SHA1=2f70156235ffd871599facf64457040d549353b4"
  set "SPI_SHA1=1c1c0ed66d07324e560dcd9e86a322ec5e4c1e96"
  set "INTERNAL_SHA1=ac14bcea6e4ff68c88fd2302c021025a2fb47940"
) else (
  echo Usage: %~nx0 ^<stlink^|jlink^|cmsis-dap^> ^<mario^|zelda^>
  exit /b 1
)

if not exist "%UPSTREAM%" (
  echo Missing upstream resources: %UPSTREAM%
  exit /b 1
)
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%" >nul 2>&1
if not exist "%MARKER_DIR%" mkdir "%MARKER_DIR%" >nul 2>&1

set "OPENOCD_EXE="
if defined OPENOCD if exist "%OPENOCD%" set "OPENOCD_EXE=%OPENOCD%"
if not defined OPENOCD_EXE if exist "%TOOL_ROOT%\openocd\bin\openocd.exe" set "OPENOCD_EXE=%TOOL_ROOT%\openocd\bin\openocd.exe"
if not defined OPENOCD_EXE if exist "%TOOL_ROOT%\openocd\openocd.exe" set "OPENOCD_EXE=%TOOL_ROOT%\openocd\openocd.exe"
if not defined OPENOCD_EXE if exist "%UPSTREAM%\openocd\bin\openocd.exe" set "OPENOCD_EXE=%UPSTREAM%\openocd\bin\openocd.exe"
if not defined OPENOCD_EXE if exist "C:\ST\STM32CubeIDE_1.18.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.openocd.win32_2.4.400.202601091506\tools\bin\openocd.exe" set "OPENOCD_EXE=C:\ST\STM32CubeIDE_1.18.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.openocd.win32_2.4.400.202601091506\tools\bin\openocd.exe"
if not defined OPENOCD_EXE if exist "C:\Program Files (x86)\LBTool\openocd-toolbox-master\OpenOCD-20210519-0.11.0\bin\openocd.exe" set "OPENOCD_EXE=C:\Program Files (x86)\LBTool\openocd-toolbox-master\OpenOCD-20210519-0.11.0\bin\openocd.exe"
if not defined OPENOCD_EXE (
  echo Cannot find openocd.exe. Set OPENOCD or place OpenOCD under service_tool\openocd.
  exit /b 2
)
if not defined OPENOCD_SCRIPTS if exist "C:\Program Files (x86)\LBTool\openocd-toolbox-master\OpenOCD-20210519-0.11.0\share\openocd\scripts" set "OPENOCD_SCRIPTS=C:\Program Files (x86)\LBTool\openocd-toolbox-master\OpenOCD-20210519-0.11.0\share\openocd\scripts"
if not defined OPENOCD_SCRIPTS set "OPENOCD_SCRIPTS=%UPSTREAM%"

set "PY_EXE="
if defined GW_SERVICE_INTERNAL_EXE set PY_EXE="%GW_SERVICE_INTERNAL_EXE%" --internal-python
if not defined PY_EXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PY_EXE if exist "C:\Users\serji\AppData\Local\Programs\Python\Python313\python.exe" set "PY_EXE=C:\Users\serji\AppData\Local\Programs\Python\Python313\python.exe"
if not defined PY_EXE (
  where py >nul 2>&1
  if not errorlevel 1 set "PY_EXE=py -3"
)
if not defined PY_EXE (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_EXE=python"
)
if not defined PY_EXE (
  echo Cannot find Python. Install Python or add it to PATH.
  exit /b 2
)

echo CONFIG adapter=%ADAPTER% target=%TARGET% speed_khz=%OPENOCD_ADAPTER_SPEED% large_flash=%LARGE_FLASH% skip_spi_sha1=%GW_SERVICE_SKIP_SPI_SHA1%
echo CONFIG gnw_frequency=%GNW_FREQUENCY%
echo CONFIG openocd=%OPENOCD_EXE%
echo CONFIG scripts=%OPENOCD_SCRIPTS%
echo CONFIG backups=%BACKUP_DIR%
echo CONFIG markers=%MARKER_DIR%

exit /b 0
