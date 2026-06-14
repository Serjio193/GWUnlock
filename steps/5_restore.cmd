@echo off
setlocal EnableExtensions EnableDelayedExpansion
call "%~dp0common.cmd" %*
if errorlevel 1 exit /b %ERRORLEVEL%

if not "%GW_SERVICE_ASSUME_YES%"=="1" (
  echo Restore writes SPI and internal flash. Run it from the GUI confirmation flow.
  exit /b 1
)

pushd "%UPSTREAM%" || exit /b 1
echo.>> "logs\5_openocd.log"
echo ===== RESTORE %DATE% %TIME% target=%TARGET% speed=%OPENOCD_ADAPTER_SPEED% =====>> "logs\5_openocd.log"
if exist "%BACKUPS%\flash_backup.bin" if exist "%BACKUPS%\internal_flash_backup.bin" if /i "%TARGET%"=="mario" (
  if not exist "%BACKUPS%\flash_backup_mario.bin" ren "%BACKUPS%\flash_backup.bin" "flash_backup_mario.bin"
  if not exist "%BACKUPS%\internal_flash_backup_mario.bin" ren "%BACKUPS%\internal_flash_backup.bin" "internal_flash_backup_mario.bin"
)

if not exist "%BACKUPS%\internal_flash_backup_%TARGET%.bin" (
  echo No backup of internal flash found in %BACKUPS%\internal_flash_backup_%TARGET%.bin.
  popd
  exit /b 1
)
if not exist "%BACKUPS%\flash_backup_%TARGET%.bin" (
  echo No backup of SPI flash found in %BACKUPS%\flash_backup_%TARGET%.bin.
  popd
  exit /b 1
)
if not exist "%MARKERS%\spi_size_%TARGET%.ok" (
  echo SPI flash size is missing. Reading it from device now.
  %PY_EXE% -u "%TOOL_ROOT%\tools\gnw_spi_progress.py" --frequency %GNW_FREQUENCY% info-ext > "logs\5_spi_size_current.log" 2>&1
  set "SPI_SIZE_RC=!ERRORLEVEL!"
  type "logs\5_spi_size_current.log"
  if not "!SPI_SIZE_RC!"=="0" (
    echo SPI flash size is UNKNOWN. Check ST-Link connection, SWD wiring, and device power.
    popd
    exit /b 1
  )
  for /f "tokens=2" %%S in ('findstr /B /C:"GNW_FLASH_SIZE " "logs\5_spi_size_current.log"') do set "SPI_EXPECTED_SIZE=%%S"
  if not defined SPI_EXPECTED_SIZE (
    echo SPI flash size is UNKNOWN. Check ST-Link connection, SWD wiring, and device power.
    popd
    exit /b 1
  )
  echo !SPI_EXPECTED_SIZE!>"%MARKERS%\spi_size_%TARGET%.ok"
  echo SPI flash size: !SPI_EXPECTED_SIZE! bytes
)
if not defined SPI_EXPECTED_SIZE set /p SPI_EXPECTED_SIZE=<"%MARKERS%\spi_size_%TARGET%.ok"
if not defined SPI_EXPECTED_SIZE (
  echo SPI flash size is missing. Run Step 1 first.
  popd
  exit /b 1
)
for %%F in ("%BACKUPS%\flash_backup_%TARGET%.bin") do set "SPI_SIZE=%%~zF"
for %%F in ("%BACKUPS%\internal_flash_backup_%TARGET%.bin") do set "MCU_SIZE=%%~zF"
if %SPI_SIZE% LEQ 0 (
  echo SPI backup is empty. Restore cancelled.
  popd
  exit /b 1
)
set /a SPI_REMAINDER=%SPI_SIZE% %% 4096
if not "%SPI_REMAINDER%"=="0" (
  echo SPI backup has invalid alignment: %SPI_SIZE% bytes. Expected a 4096-byte aligned image.
  popd
  exit /b 1
)
if %SPI_SIZE% GTR %SPI_EXPECTED_SIZE% (
  echo SPI backup has unexpected size: %SPI_SIZE% bytes. Device SPI is %SPI_EXPECTED_SIZE% bytes.
  popd
  exit /b 1
)
if not "%SPI_SIZE%"=="%SPI_EXPECTED_SIZE%" (
  echo SPI backup is smaller than detected SPI: %SPI_SIZE% bytes of %SPI_EXPECTED_SIZE% bytes. Restoring this image at SPI base address.
)
echo Restore source SPI: %BACKUPS%\flash_backup_%TARGET%.bin (%SPI_SIZE% bytes)
echo Restore source MCU: %BACKUPS%\internal_flash_backup_%TARGET%.bin (%MCU_SIZE% bytes)
echo Restore config adapter=%ADAPTER% target=%TARGET% speed_khz=%OPENOCD_ADAPTER_SPEED% gnw_frequency=%GNW_FREQUENCY%
echo Restore openocd=%OPENOCD_EXE%
echo Restore scripts=%OPENOCD_SCRIPTS%
echo Restore SPI address=0x90000000
echo Restore MCU address=0x08000000 length=131072
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" describe-file "%BACKUPS%\flash_backup_%TARGET%.bin" "SPI_SOURCE"
if errorlevel 1 (
  echo Failed to describe SPI source.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" describe-file "%BACKUPS%\internal_flash_backup_%TARGET%.bin" "MCU_SOURCE"
if errorlevel 1 (
  echo Failed to describe MCU source.
  popd
  exit /b 1
)
if not "%MCU_SIZE%"=="131072" (
  echo MCU backup has unexpected size. Expected 131072 bytes.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" validate-internal "%BACKUPS%\internal_flash_backup_%TARGET%.bin"
if errorlevel 1 (
  echo MCU backup is not a valid STM32 firmware image. Restore cancelled.
  popd
  exit /b 1
)

echo [phase] Restoring and verifying SPI flash.
echo Restoring SPI flash through GNWManager helper...
%PY_EXE% -u "%TOOL_ROOT%\tools\gnw_spi_progress.py" --frequency %GNW_FREQUENCY% write-ext --expected-size %SPI_EXPECTED_SIZE% --input "%BACKUPS%\flash_backup_%TARGET%.bin"
if errorlevel 1 (
  echo Restoring SPI flash failed.
  popd
  exit /b 1
)

echo [phase] Programming and verifying MCU internal flash.
echo Restoring internal flash address=0x08000000 length=131072 file=%BACKUPS%\internal_flash_backup_%TARGET%.bin
del /q "%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin" >nul 2>&1
"%OPENOCD_EXE%" -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/target_%TARGET%.cfg" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -c "program {%BACKUPS_TCL%/internal_flash_backup_%TARGET%.bin} 0x08000000 verify;" -c "halt;" -c "dump_image {%BACKUPS_TCL%/internal_flash_restore_verify_%TARGET%.bin} 0x08000000 131072;" -c "exit;" >> "logs\5_openocd.log" 2>&1
if errorlevel 1 (
  echo Restoring or reading back internal flash failed. Check logs\5_openocd.log.
  popd
  exit /b 1
)
findstr /C:"** Programming Started **" /C:"** Programming Finished **" /C:"** Verify Started **" /C:"** Verified OK **" "logs\5_openocd.log"

echo [phase] Reading MCU back for final compare.
echo MCU readback address=0x08000000 length=131072 file=%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin
if not exist "%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin" (
  echo MCU readback verification failed. Check logs\5_openocd.log.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" describe-file "%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin" "MCU_READBACK"
if errorlevel 1 (
  echo Failed to describe MCU readback.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" compare-files "%BACKUPS%\internal_flash_backup_%TARGET%.bin" "%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin" "MCU_COMPARE"
if errorlevel 1 (
  echo MCU readback does not match backup. Check logs\5_openocd.log.
  popd
  exit /b 1
)
%PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" sha1 "%BACKUPS%\internal_flash_backup_%TARGET%.bin" > "%MARKERS%\restore_mcu_verified_%TARGET%.ok"
copy /y "%MARKERS%\restore_mcu_verified_%TARGET%.ok" "%BACKUPS%\internal_flash_restore_verify_%TARGET%.sha1" >nul
del /q "%BACKUPS%\internal_flash_restore_verify_%TARGET%.bin" >nul 2>&1

echo Restore completed. Power-cycle the device.
echo IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.
break > "%MARKERS%\restore_%TARGET%.ok"
del /q "%MARKERS%\unlock_%TARGET%.ok" >nul 2>&1
del /q "%MARKERS%\protection_unlocked_%TARGET%.ok" >nul 2>&1
popd
exit /b 0
