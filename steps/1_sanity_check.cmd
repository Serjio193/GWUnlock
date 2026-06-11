@echo off
setlocal EnableExtensions EnableDelayedExpansion
call "%~dp0common.cmd" %*
if errorlevel 1 exit /b %ERRORLEVEL%

pushd "%UPSTREAM%" || exit /b 1
echo Running sanity checks...
del /q "%MARKERS%\sanity_%TARGET%.ok" >nul 2>&1
del /q "%BACKUPS%\model_probe.bin" >nul 2>&1
"%OPENOCD_EXE%" -s "%UPSTREAM%" -s "%OPENOCD_SCRIPTS%" -f "openocd/target_mario.cfg" -f "openocd/interface_%ADAPTER%.cfg" -c "init;" -c "halt;" -c "dump_image {%BACKUPS_TCL%/model_probe.bin} 0x0 1332" -c "exit;" > "logs\1_model_detect_current.log" 2>&1
set "MODEL_RC=!ERRORLEVEL!"
echo.>> "logs\1_model_detect.log"
echo ===== MODEL CHECK %DATE% %TIME% =====>> "logs\1_model_detect.log"
type "logs\1_model_detect_current.log" >> "logs\1_model_detect.log"
if "!MODEL_RC!"=="0" (
  set "DETECTED_MODEL="
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" detect-model "%BACKUPS%\model_probe.bin" > "logs\1_model_parse.tmp"
  for /f "tokens=3" %%M in (logs\1_model_parse.tmp) do (
    if /i "%%M"=="mario" set "DETECTED_MODEL=mario"
    if /i "%%M"=="zelda" set "DETECTED_MODEL=zelda"
  )
  del /q "logs\1_model_parse.tmp" >nul 2>&1
) else (
  set "DETECTED_MODEL="
)
del /q "%BACKUPS%\model_probe.bin" >nul 2>&1
if not defined DETECTED_MODEL if exist "%BACKUPS%\flash_backup_%TARGET%.bin" (
  %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" detect-model-spi "%BACKUPS%\flash_backup_%TARGET%.bin" > "logs\1_model_parse.tmp"
  for /f "tokens=3" %%M in (logs\1_model_parse.tmp) do (
    if /i "%%M"=="mario" set "DETECTED_MODEL=mario"
    if /i "%%M"=="zelda" set "DETECTED_MODEL=zelda"
  )
  del /q "logs\1_model_parse.tmp" >nul 2>&1
)
if not defined DETECTED_MODEL (
  for %%F in ("%BACKUPS%\flash_backup_*.bin") do if not defined DETECTED_MODEL (
    %PY_EXE% "%TOOL_ROOT%\tools\win_ops.py" detect-model-spi "%%~fF" > "logs\1_model_parse.tmp"
    for /f "tokens=3" %%M in (logs\1_model_parse.tmp) do if /i not "%%M"=="unknown" set "DETECTED_MODEL=%%M"
    del /q "logs\1_model_parse.tmp" >nul 2>&1
  )
)
if /i "!DETECTED_MODEL!"=="mario" set "TARGET=mario"
if /i "!DETECTED_MODEL!"=="zelda" set "TARGET=zelda"
del /q "%MARKERS%\model_mario.ok" "%MARKERS%\model_zelda.ok" >nul 2>&1
if defined DETECTED_MODEL (
  echo Detected model: !DETECTED_MODEL!
  break > "%MARKERS%\model_!DETECTED_MODEL!.ok"
) else (
  echo Detected model: unknown
)
del /q "%MARKERS%\protection_locked_%TARGET%.ok" >nul 2>&1
del /q "%MARKERS%\protection_unlocked_%TARGET%.ok" >nul 2>&1
%PY_EXE% "%TOOL_ROOT%\tools\protection_check.py" %GNW_FREQUENCY% > "logs\1_protection_current.log" 2>&1
set "PROTECTION_RC=!ERRORLEVEL!"
echo.>> "logs\1_protection.log"
echo ===== PROTECTION CHECK %DATE% %TIME% =====>> "logs\1_protection.log"
type "logs\1_protection_current.log" >> "logs\1_protection.log"
type "logs\1_protection_current.log"
if "!PROTECTION_RC!"=="0" (
  findstr /C:"Protection: UNLOCKED" "logs\1_protection_current.log" >nul 2>&1
  if not errorlevel 1 (
    break > "%MARKERS%\protection_unlocked_%TARGET%.ok"
    del /q "%MARKERS%\protection_locked_%TARGET%.ok" >nul 2>&1
  ) else (
    break > "%MARKERS%\protection_locked_%TARGET%.ok"
    del /q "%MARKERS%\unlock_%TARGET%.ok" >nul 2>&1
  )
) else (
  del /q "%MARKERS%\unlock_%TARGET%.ok" >nul 2>&1
  del /q "%MARKERS%\protection_locked_%TARGET%.ok" "%MARKERS%\protection_unlocked_%TARGET%.ok" >nul 2>&1
  echo Protection status is UNKNOWN. Check ST-Link connection, SWD wiring, and device power.
  popd
  exit /b 1
)

"%OPENOCD_EXE%" -v >nul 2>&1
if errorlevel 1 (
  echo OpenOCD does not seem to be working.
  popd
  exit /b 1
)

%PY_EXE% -V >nul 2>&1
if errorlevel 1 (
  echo Python does not seem to be working.
  popd
  exit /b 1
)

if not exist "openocd\interface_%ADAPTER%.cfg" (
  echo Missing adapter config: openocd\interface_%ADAPTER%.cfg
  popd
  exit /b 1
)
if not exist "openocd\target_%TARGET%.cfg" (
  echo Missing target config: openocd\target_%TARGET%.cfg
  popd
  exit /b 1
)
if not exist "openocd\rdp0.cfg" (
  echo Missing unlock config: openocd\rdp0.cfg
  popd
  exit /b 1
)
if not exist "payload\payload.bin" (
  echo Missing payload\payload.bin
  popd
  exit /b 1
)

echo Looks good.
break > "%MARKERS%\sanity_%TARGET%.ok"
popd
exit /b 0
