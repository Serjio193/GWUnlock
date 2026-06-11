@echo off
setlocal EnableExtensions EnableDelayedExpansion
call "%~dp0common.cmd" %*
if errorlevel 1 exit /b %ERRORLEVEL%

if not "%GW_SERVICE_ASSUME_YES%"=="1" (
  echo This step modifies SPI flash. Run it from the GUI confirmation flow.
  exit /b 1
)

pushd "%UPSTREAM%" || exit /b 1
echo.>> "logs\3_openocd.log"
echo ===== INTERNAL BACKUP %DATE% %TIME% target=%TARGET% speed=%OPENOCD_ADAPTER_SPEED% =====>> "logs\3_openocd.log"
if not exist "%BACKUPS%\flash_backup_%TARGET%.bin" (
  echo SPI backup is missing. Run Step 2 first.
  popd
  exit /b 1
)
if not exist "%MARKERS%\spi_size_%TARGET%.ok" (
  echo SPI flash size is missing. Run Step 1 first.
  popd
  exit /b 1
)
set /p SPI_EXPECTED_SIZE=<"%MARKERS%\spi_size_%TARGET%.ok"
if not defined SPI_EXPECTED_SIZE (
  echo SPI flash size is missing. Run Step 1 first.
  popd
  exit /b 1
)
for %%F in ("%BACKUPS%\flash_backup_%TARGET%.bin") do set "SPI_SIZE=%%~zF"
if not "%SPI_SIZE%"=="%SPI_EXPECTED_SIZE%" (
  echo SPI backup has unexpected size: %SPI_SIZE% bytes. Expected %SPI_EXPECTED_SIZE% bytes from Step 1.
  popd
  exit /b 1
)
set "ITCM_FILE=%BACKUPS%\itcm_backup_%TARGET%.bin"
if not exist "%ITCM_FILE%" (
  echo Valid ITCM backup is missing for target %TARGET%.
  echo Run Step 2 on a stock booting device first. Keep %BACKUPS%\itcm_backup_%TARGET%.bin together with the SPI and MCU backups.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-model-itcm "%ITCM_FILE%" "%TARGET%"
if errorlevel 1 (
  echo Valid ITCM backup is missing for target %TARGET%.
  echo Run Step 2 again and keep the generated ITCM file together with the SPI and MCU backups.
  popd
  exit /b 1
)
if exist "%BACKUPS%\internal_flash_backup_%TARGET%.bin" (
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\internal_flash_backup_%TARGET%.bin" "%INTERNAL_SHA1%"
  if not errorlevel 1 (
    echo Already have valid %BACKUPS%\internal_flash_backup_%TARGET%.bin, refusing to overwrite.
    del /q "new_flash_image.bin" >nul 2>&1
    del /q "%MARKERS%\payload_pending_%TARGET%.ok" >nul 2>&1
    break > "%MARKERS%\internal_backup_%TARGET%.ok"
    popd
    exit /b 0
  )
  if exist "%MARKERS%\internal_backup_%TARGET%.ok" if exist "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1" (
    echo Already have stable custom %BACKUPS%\internal_flash_backup_%TARGET%.bin, refusing to overwrite.
    popd
    exit /b 0
  )
  set "FAILED_NAME=internal_flash_backup_%TARGET%.bin.failed_%DATE:/=-%_%TIME::=-%"
  set "FAILED_NAME=!FAILED_NAME: =_!"
  set "FAILED_NAME=!FAILED_NAME:,=!"
  echo Existing internal flash backup is invalid. Renaming to !FAILED_NAME!
  ren "%BACKUPS%\internal_flash_backup_%TARGET%.bin" "!FAILED_NAME!"
)

if exist "%MARKERS%\payload_pending_%TARGET%.ok" if not "%GW_SERVICE_PAYLOAD_CONFIRMED%"=="1" (
  echo Payload image exists, but payload boot mode was not confirmed.
  echo Power-cycle the device, hold Power, wait for the blue screen, then run Step 3 from the GUI and confirm the prompt.
  popd
  exit /b 1
)
if exist "%MARKERS%\payload_pending_%TARGET%.ok" goto dump_internal
if exist "new_flash_image.bin" (
  echo Removing stale payload image from an incomplete previous attempt.
  del /q "new_flash_image.bin" >nul 2>&1
)

echo [phase] Preparing payload image for internal flash backup.
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" slice "%BACKUPS%\flash_backup_%TARGET%.bin" "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" %SPIFLASH_SKIP_16% %SPIFLASH_COUNT_16%
if errorlevel 1 (
  echo Failed to access %BACKUPS%\flash_backup_%TARGET%.bin. Run step 2 first.
  popd
  exit /b 1
)

%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" "%SPI_SHA1%"
if errorlevel 1 (
  if "%GW_SERVICE_SKIP_SPI_SHA1%"=="1" (
    echo WARNING: External flash checksum mismatch ignored because GW_SERVICE_SKIP_SPI_SHA1=1.
    goto :verify_itcm
  )
  echo External flash backup does not verify correctly.
  popd
  exit /b 1
)

:verify_itcm
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-model-itcm "%ITCM_FILE%" "%TARGET%"
if errorlevel 1 (
  echo ITCM dump does not verify correctly.
  popd
  exit /b 1
)
del /q "%BACKUPS%\flash_backup_checksummed_%TARGET%.bin" >nul 2>&1

echo Generating encrypted flash image from backed up data...
%PY_EXE% "python\tcm_encrypt.py" "%BACKUPS%\flash_backup_%TARGET%.bin" %FLASH_OFFSET% "%ITCM_FILE%" "payload\payload.bin" "new_flash_image.bin"
if errorlevel 1 (
  echo Failed to build encrypted flash image.
  popd
  exit /b 1
)

echo [stage] payload_write Programming payload to SPI flash...
echo [phase] Programming payload image to SPI flash. This can take several minutes.
%PY_EXE% -u "%TOOL_ROOT%\tools\gnw_spi_progress.py" --frequency %GNW_FREQUENCY% write-ext --expected-size %SPI_EXPECTED_SIZE% --input "new_flash_image.bin"
if errorlevel 1 (
  del /q "new_flash_image.bin" >nul 2>&1
  del /q "%MARKERS%\payload_pending_%TARGET%.ok" >nul 2>&1
  echo Writing payload to SPI flash failed.
  echo Recovery procedure:
  echo - Disconnect and reconnect power
  echo - Press the Power button once
  echo - Do not hold the Power button at this stage
  echo - Run Step 3 again
  popd
  exit /b 1
)

echo [stage] payload_done Payload programmed.
break > "%MARKERS%\payload_pending_%TARGET%.ok"
echo Flash successfully programmed. Now do the following procedure:
echo - Disconnect power from the device
echo - Power it again
echo - Press and hold the power button on the device
echo - The LCD should show a blue screen
echo - If it is not blue, try pressing the Time button on the device
echo - Then press Step 3 again in this tool while still holding the power button
popd
exit /b 0

:dump_internal
echo [phase] Payload mode confirmed. Reading internal flash from SRAM mirror.
echo Dumping internal flash...
del /q "%BACKUPS%\internal_flash_candidate_%TARGET%.bin" "%BACKUPS%\internal_flash_candidate_%TARGET%.bin.second" >nul 2>&1
"%OPENOCD_EXE%" -d2 -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -c "reg;" -c "mdw 0x24000000 8;" -c "dump_image {%BACKUPS_TCL%/internal_flash_candidate_%TARGET%.bin} 0x24000000 131072" -c "exit;" >> "logs\3_openocd.log" 2>&1
if errorlevel 1 (
  echo Dumping internal flash failed. Check logs\3_openocd.log.
  popd
  exit /b 1
)

echo Verifying internal flash backup...
set "EXPECTED_INTERNAL_SHA1=%INTERNAL_SHA1%"
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" verify-digest "%BACKUPS%\internal_flash_candidate_%TARGET%.bin" "%EXPECTED_INTERNAL_SHA1%"
if errorlevel 1 (
  echo Official internal flash SHA1 mismatch. Trying stable duplicate verification for custom device state.
  echo Dumping internal flash second pass...
  "%OPENOCD_EXE%" -d2 -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -c "reg;" -c "mdw 0x24000000 8;" -c "dump_image {%BACKUPS_TCL%/internal_flash_candidate_%TARGET%.bin.second} 0x24000000 131072" -c "exit;" >> "logs\3_openocd.log" 2>&1
  if errorlevel 1 (
    echo Second internal flash dump failed. Check logs\3_openocd.log.
    popd
    exit /b 1
  )
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" stable-internal "%BACKUPS%\internal_flash_candidate_%TARGET%.bin" "%BACKUPS%\internal_flash_candidate_%TARGET%.bin.second" "%MARKERS%\internal_backup_%TARGET%.ok" "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1"
  if errorlevel 1 (
    echo The backup of the internal flash failed.
    del /q "%MARKERS%\internal_backup_%TARGET%.ok" >nul 2>&1
    popd
    exit /b 1
  )
  move /y "%BACKUPS%\internal_flash_candidate_%TARGET%.bin" "%BACKUPS%\internal_flash_backup_%TARGET%.bin" >nul
  del /q "%BACKUPS%\internal_flash_candidate_%TARGET%.bin.second" >nul 2>&1
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" sha1 "%BACKUPS%\internal_flash_backup_%TARGET%.bin" > "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1"
) else (
  move /y "%BACKUPS%\internal_flash_candidate_%TARGET%.bin" "%BACKUPS%\internal_flash_backup_%TARGET%.bin" >nul
  del /q "%BACKUPS%\internal_flash_backup_%TARGET%.bin.actual.sha1" >nul 2>&1
)

del /q "new_flash_image.bin" >nul 2>&1
del /q "%MARKERS%\payload_pending_%TARGET%.ok" >nul 2>&1
break > "%MARKERS%\internal_backup_%TARGET%.ok"
echo Device backed up successfully.
echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
popd
exit /b 0
