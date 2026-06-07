@echo off
setlocal EnableExtensions
call "%~dp0common.cmd" %*
if errorlevel 1 exit /b %ERRORLEVEL%

if not "%GW_SERVICE_ASSUME_YES%"=="1" (
  echo Unlock erases internal flash. Run it from the GUI confirmation flow.
  exit /b 1
)

pushd "%UPSTREAM%" || exit /b 1
if not exist "%BACKUPS%\internal_flash_backup_%TARGET%.bin" (
  echo Internal flash backup is missing. Complete Step 3 before unlock.
  popd
  exit /b 1
)
echo Validating internal flash backup before unlock...
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\internal_flash_backup_%TARGET%.bin" "%INTERNAL_SHA1%"
if errorlevel 1 (
  if exist "%MARKERS%\internal_backup_%TARGET%.ok" if exist "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1" (
    echo Official SHA1 does not match, but stable custom internal backup marker exists.
    type "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1"
  ) else (
    echo Backup is not valid. Aborting.
    popd
    exit /b 1
  )
)

echo Unlocking device. This erases internal flash.
"%OPENOCD_EXE%" -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -f "openocd/rdp0.cfg" >> "logs\4_openocd.log" 2>&1
if errorlevel 1 (
  echo Unlocking device failed. Check logs\4_openocd.log.
  popd
  exit /b 1
)

echo Device unlocked. Power-cycle the device, then run restore.
echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
break > "%MARKERS%\unlock_%TARGET%.ok"
break > "%MARKERS%\protection_unlocked_%TARGET%.ok"
popd
exit /b 0
