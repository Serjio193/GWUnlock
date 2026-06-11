@echo off
setlocal EnableExtensions EnableDelayedExpansion
call "%~dp0common.cmd" %*
if errorlevel 1 exit /b %ERRORLEVEL%

pushd "%UPSTREAM%" || exit /b 1
echo.>> "logs\2_openocd.log"
echo ===== SPI BACKUP %DATE% %TIME% target=%TARGET% speed=%OPENOCD_ADAPTER_SPEED% =====>> "logs\2_openocd.log"
tasklist /FI "IMAGENAME eq gw_studio_tauri.exe" 2>nul | find /I "gw_studio_tauri.exe" >nul
if not errorlevel 1 (
  echo ST-Link is busy: another application is using the programmer.
  echo Close other programmer/debugger applications, then retry Step 2.
  popd
  exit /b 1
)
tasklist /FI "IMAGENAME eq GWStudio.exe" 2>nul | find /I "GWStudio.exe" >nul
if not errorlevel 1 (
  echo ST-Link is busy: another application is using the programmer.
  echo Close other programmer/debugger applications, then retry Step 2.
  popd
  exit /b 1
)
if not exist "%MARKERS%\sanity_%TARGET%.ok" (
  echo Step 1 did not complete successfully.
  echo Check ST-Link connection, SWD wiring, and device power, then run Step 1 again.
  popd
  exit /b 1
)
if "%LARGE_FLASH%"=="1" goto :skip_standard_overwrite_check
if exist "%BACKUPS%\flash_backup_%TARGET%.bin" (
  echo Already have %BACKUPS%\flash_backup_%TARGET%.bin, refusing to overwrite.
  popd
  exit /b 1
)
:skip_standard_overwrite_check

echo Attempting to dump SPI flash using adapter %ADAPTER%.
if "%LARGE_FLASH%"=="1" goto :large_flash_dump
"%OPENOCD_EXE%" -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/target_%TARGET%.cfg" -f "openocd/interface_%ADAPTER%.cfg" -f "openocd/flash.cfg" >> "logs\2_openocd.log" 2>&1
if errorlevel 1 (
  echo Failed to dump SPI flash from device. Check logs\2_openocd.log.
  popd
  exit /b 1
)

echo Validating ITCM dump...
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\itcm_backup_%TARGET%.bin" "%ITCM_SHA1%"
if errorlevel 1 (
  echo Failed to correctly dump ITCM.
  popd
  exit /b 1
)

echo Extracting checksummed SPI range...
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" slice "%BACKUPS%\flash_backup_%TARGET%.bin" "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" %SPIFLASH_SKIP_16% %SPIFLASH_COUNT_16%
if errorlevel 1 (
  echo Failed to access flash_backup_%TARGET%.bin.
  popd
  exit /b 1
)

echo Validating SPI checksum...
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" "%SPI_SHA1%"
if errorlevel 1 (
  if "%GW_SERVICE_SKIP_SPI_SHA1%"=="1" (
  echo WARNING: SPI checksum mismatch ignored because GW_SERVICE_SKIP_SPI_SHA1=1.
  del /q "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" >nul 2>&1
  echo Successfully backed up SPI flash to %BACKUPS%\flash_backup_%TARGET%.bin.
  echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
  break > "%MARKERS%\spi_backup_%TARGET%.ok"
    popd
    exit /b 0
  )
  echo Failed to verify checksum of the external flash.
  popd
  exit /b 1
)

del /q "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" >nul 2>&1
echo Successfully backed up SPI flash to %BACKUPS%\flash_backup_%TARGET%.bin.
echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
break > "%MARKERS%\spi_backup_%TARGET%.ok"
popd
exit /b 0

:large_flash_dump
if exist "%BACKUPS%\flash_backup_%TARGET%.bin" (
  for %%F in ("%BACKUPS%\flash_backup_%TARGET%.bin") do set "EXISTING_SIZE=%%~zF"
  if not "!EXISTING_SIZE!"=="67108864" (
    set "PARTIAL_NAME=flash_backup_%TARGET%.bin.partial_%DATE:/=-%_%TIME::=-%"
    set "PARTIAL_NAME=!PARTIAL_NAME: =_!"
    set "PARTIAL_NAME=!PARTIAL_NAME:,=!"
    echo Existing SPI backup is incomplete: !EXISTING_SIZE! bytes. Renaming to !PARTIAL_NAME!
    ren "%BACKUPS%\flash_backup_%TARGET%.bin" "!PARTIAL_NAME!"
  ) else (
    echo Already have complete %BACKUPS%\flash_backup_%TARGET%.bin, refusing to overwrite.
    popd
    exit /b 1
  )
)
echo Dumping ITCM bootstrap area for unlock flow.
if exist "%BACKUPS%\itcm_backup_%TARGET%.bin" (
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\itcm_backup_%TARGET%.bin" "%ITCM_SHA1%"
  if not errorlevel 1 (
    echo Existing ITCM backup is valid. Reusing it.
    goto :read_large_spi
  )
)
del /q "%BACKUPS%\itcm_backup_%TARGET%.bin" >nul 2>&1
set "ITCM_OK=0"
for /l %%R in (1,1,3) do (
  echo ITCM read attempt %%R/3.
  "%OPENOCD_EXE%" -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/target_%TARGET%.cfg" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -c "dump_image {%BACKUPS_TCL%/itcm_backup_%TARGET%.bin} %ITCM_OFFSET% %ITCM_LENGTH%" -c "exit;" >> "logs\2_openocd.log" 2>&1
  if not errorlevel 1 (
    set "ITCM_OK=1"
    goto :itcm_done
  )
  timeout /t 2 /nobreak >nul
)

:itcm_done
if not "%ITCM_OK%"=="1" (
  echo ITCM read failed: ST-Link is busy or the target is not reachable.
  echo Close other programmer/debugger applications, then retry Step 2.
  goto :large_flash_failed
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\itcm_backup_%TARGET%.bin" "%ITCM_SHA1%"
if errorlevel 1 (
  set "INVALID_ITCM=itcm_backup_%TARGET%.bin.invalid_%DATE:/=-%_%TIME::=-%"
  set "INVALID_ITCM=!INVALID_ITCM: =_!"
  set "INVALID_ITCM=!INVALID_ITCM:,=!"
  ren "%BACKUPS%\itcm_backup_%TARGET%.bin" "!INVALID_ITCM!"
  echo WARNING: ITCM is unavailable because the expected stock firmware is not running.
  echo SPI backup will continue. Step 3 will remain unavailable until a valid ITCM dump exists.
)

:read_large_spi
echo Detecting SPI flash size through GNWManager helper.
echo Dumping SPI flash through GNWManager helper.
%PY_EXE% -u "%TOOL_ROOT%\tools\gnw_spi_progress.py" --frequency %GNW_FREQUENCY% read-ext --chunk 2097152 --output "%BACKUPS%\flash_backup_%TARGET%.bin"
if errorlevel 1 (
  echo GNWManager SPI read failed.
  goto :large_flash_failed
)
echo Successfully backed up SPI flash to %BACKUPS%\flash_backup_%TARGET%.bin.
echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
break > "%MARKERS%\spi_backup_%TARGET%.ok"
popd
exit /b 0

:large_flash_failed
popd
exit /b 1
