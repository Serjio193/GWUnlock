from __future__ import annotations

import hashlib
import os
import runpy
import shutil
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLocale, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


FROZEN = bool(getattr(sys, "frozen", False))
APP_VERSION = "1.0.0"
BUILD_DATE = "2026-06-07"
APP_ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
ASSET_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT)).resolve()
APP_ICON = ASSET_ROOT / "resources" / "logo.ico"
APP_LOGO = ASSET_ROOT / "resources" / "logo.png"
RUNTIME_ROOT = ASSET_ROOT / "upstream"
DATA_ROOT = APP_ROOT if FROZEN else RUNTIME_ROOT
BACKUPS = DATA_ROOT / "backups"
STATE = BACKUPS / ".state" if FROZEN else RUNTIME_ROOT / "markers"
STEPS = ASSET_ROOT / "steps"
LOGS = RUNTIME_ROOT / "logs"
ROOT = APP_ROOT


def internal_python_main(arguments: list[str]) -> int:
    args = list(arguments)
    if args and args[0] == "-u":
        args.pop(0)
    if args and args[0] in ("-V", "--version"):
        print(sys.version)
        return 0
    if not args:
        print("Missing internal Python script.")
        return 2
    script = Path(args.pop(0))
    if not script.exists():
        print(f"Internal Python script not found: {script}")
        return 2
    sys.argv = [str(script), *args]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def copy_tree_contents(source: Path, destination: Path, clear: bool = False) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if clear:
        for entry in destination.iterdir():
            if entry.is_file():
                entry.unlink()
            elif entry.is_dir():
                shutil.rmtree(entry)
    if not source.exists():
        return
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, target)


def prepare_runtime() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    if not FROZEN:
        (RUNTIME_ROOT / "backups").mkdir(parents=True, exist_ok=True)
        (RUNTIME_ROOT / "markers").mkdir(parents=True, exist_ok=True)
        return
    BACKUPS.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    legacy = APP_ROOT / "upstream"
    has_backup_data = any(entry.name != ".state" for entry in BACKUPS.iterdir())
    if legacy.exists() and not has_backup_data:
        copy_tree_contents(legacy / "backups", BACKUPS)
        copy_tree_contents(legacy / "markers", STATE)
    (RUNTIME_ROOT / "backups").mkdir(parents=True, exist_ok=True)
    (RUNTIME_ROOT / "markers").mkdir(parents=True, exist_ok=True)
    sync_to_runtime()


def sync_to_runtime() -> None:
    if not FROZEN:
        return
    payload_image = STATE / "new_flash_image.bin"
    if payload_image.exists():
        shutil.copy2(payload_image, RUNTIME_ROOT / "new_flash_image.bin")


def sync_from_runtime() -> None:
    if not FROZEN:
        return
    payload_image = RUNTIME_ROOT / "new_flash_image.bin"
    if payload_image.exists():
        shutil.copy2(payload_image, STATE / "new_flash_image.bin")


def calculate_file_sha256(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def current_program_sha256() -> str:
    return calculate_file_sha256(Path(sys.executable if FROZEN else __file__))


def detect_default_language() -> str:
    name = QLocale.system().name().lower()
    if name.startswith("ru"):
        return "ru"
    if name.startswith("uk") or name.startswith("ua"):
        return "uk"
    return "en"

STEP_DEFS = [
    ("1_sanity_check.cmd", "1. Sanity check", False),
    ("2_backup_flash.cmd", "2. Backup SPI flash", False),
    ("3_backup_internal_flash.cmd", "3. Backup internal flash", True),
    ("4_unlock_device.cmd", "4. Unlock device", True),
    ("5_restore.cmd", "5. Restore", True),
]

LANGS = {
    "ru": {
        "language_name": "Русский",
        "adapter": "Адаптер",
        "target": "Модель",
        "speed": "Скорость кГц",
        "language": "Язык",
        "theme": "Тема",
        "theme_dark": "Чёрная",
        "theme_light": "Белая",
        "idle": "Ожидание",
        "running": "Выполняется",
        "busy_title": "Занято",
        "busy_text": "Уже выполняется другой шаг.",
        "missing_script": "Скрипт не найден",
        "step_locked_title": "Шаг заблокирован",
        "already_done_title": "Уже выполнено",
        "confirm_title": "Подтверждение",
        "confirm_text": "Этот шаг записывает данные в устройство или меняет защиту. Продолжить?",
        "spi_exists_title": "Резервная копия SPI уже есть",
        "spi_exists_text": "Полный SPI backup уже существует. Скрипт не будет его перезаписывать.",
        "payload_mode_title": "Режим служебной загрузки",
        "payload_mode_text": "Payload уже записан во SPI.\n\nСделай сейчас:\n1. Отключи питание устройства.\n2. Подай питание снова.\n3. Зажми кнопку Power.\n4. Дождись синего экрана.\n5. Если экран не синий, один раз нажми Time.\n6. Продолжай держать Power и нажми Да здесь.\n\nПродолжай только когда синий экран виден.",
        "payload_programmed_title": "Payload записан",
        "payload_programmed_text": "Payload записан во SPI.\n\nТеперь:\n1. Отключи питание устройства.\n2. Подай питание снова.\n3. Зажми кнопку Power.\n4. Дождись синего экрана.\n5. Если экран не синий, один раз нажми Time.\n6. Запусти Step 3 снова, продолжая держать Power.",
        "root_line": "Папка GWUnlock",
        "independent_line": "Локальный инструмент обслуживания устройства.",
        "result_ok": "Результат: OK",
        "result_failed": "Результат: ОШИБКА",
        "full_log": "Полный лог",
        "protection_unlocked": "Защита: СНЯТА",
        "protection_locked": "Защита: LOCKED",
        "protection_unknown": "Защита: не проверена",
        "spi_ok": "Резервная копия SPI: OK",
        "spi_missing": "Резервная копия SPI: нет",
        "internal_ok": "Резервная копия MCU: OK",
        "internal_wait": "Резервная копия MCU: ожидается синий экран",
        "internal_invalid": "Резервная копия MCU: неверная",
        "internal_missing": "Резервная копия MCU: нет",
        "unlock_done": "Разблокировка: выполнена",
        "unlock_not_done": "Разблокировка: не выполнена",
        "restore_done": "Восстановление: выполнено",
        "restore_not_done": "Восстановление: не выполнено",
        "disabled_unlocked": "Данная консоль уже разблокирована. Доступно только восстановление при наличии резервных копий.",
        "disabled_generic": "Этот шаг отключён текущим состоянием.",
        "already_1": "Проверка уже отмечена OK. Запустить снова?",
        "already_2": "Полный SPI backup уже есть. Запустить снова?",
        "already_3": "Валидный internal backup уже есть. Запустить снова?",
        "already_4": "Разблокировка уже отмечена выполненной. Запустить снова?",
        "already_5": "Восстановление уже отмечено выполненным. Запустить снова?",
        "step_1": "1. Проверка защиты",
        "step_2": "2. Копия SPI flash",
        "step_3": "3. Копия памяти MCU",
        "step_4": "4. Разблокировка",
        "step_5": "5. Восстановление",
        "instr_1": "Проверяет локальные инструменты и показывает состояние защиты.",
        "instr_2": "Создаёт SPI backup. Жди, пока одна полоса прогресса дойдёт до 100%.",
        "instr_3_phase2": "Фаза 2: передёрни питание, зажми Power, дождись синего экрана, подтверди и продолжай держать Power.",
        "instr_3_phase1": "Фаза 1: пишет payload во SPI. Если ошибка, передёрни питание и один раз нажми Power, не держи, потом повтори.",
        "instr_4": "Разблокировка стирает внутреннюю память MCU. После OK передёрни питание и запусти шаг 5.",
        "instr_5": "Восстанавливает SPI и внутреннюю память MCU из резервных копий. После OK передёрни питание устройства.",
        "success_4": "OK: устройство разблокировано. Передёрни питание, затем запусти шаг 5.",
        "success_5": "OK: восстановление завершено. Передёрни питание устройства.",
        "success_3_payload": "OK: payload записан. Сделай процедуру синего экрана и снова запусти Step 3.",
        "success_generic": "OK: шаг выполнен.",
        "fail_3": "ОШИБКА: выполни показанные действия восстановления и повтори Step 3.",
        "fail_5": "ОШИБКА: восстановление не завершено. Смотри подробности ниже.",
        "fail_generic": "ОШИБКА: смотри полный лог ниже.",
        "running_step": "Выполняется",
        "payload_write": "Запись payload",
        "payload_programmed": "Payload записан",
        "spi_read": "Чтение SPI",
        "spi_write": "Запись SPI",
        "spi_verify": "Проверка SPI",
        "waiting_data": "ожидание данных",
        "step_active": "Шаг активен",
        "log": "лог",
        "estimated": "оценка",
        "yes": "Да",
        "no": "Нет",
        "backup_rotated": "Предыдущий SPI backup переименован",
        "backup_warning": "Важно: сохрани папку backups в безопасном месте. Для восстановления нужны SPI backup, MCU backup и ITCM backup этой же консоли.",
        "need_internal_backup": "Сначала полностью заверши шаг 3 и получи зелёный статус MCU backup.",
        "continue": "Далее",
        "step3_continue": "Payload записан. Отключи и снова подай питание, зажми Power, дождись синего экрана. Не отпуская Power, нажми «Далее».",
        "already_unlocked_with_backup": "Данная консоль уже разблокирована. Резервные копии найдены, доступно только восстановление.",
        "already_unlocked_no_backup": "Данная консоль уже разблокирована. Резервные копии не найдены, восстановление недоступно.",
        "driver_title": "Требуется драйвер программатора",
        "driver_text": "Windows обнаружила программатор, но драйвер работает неправильно.\n\nОткрыть официальную страницу установки драйвера?",
        "sha_line": "SHA256 программы",
        "auto_read_after_unlock": "Разблокировка завершена. Автоматически перечитываю информацию устройства...",
    },
    "uk": {
        "language_name": "Українська",
        "adapter": "Адаптер",
        "target": "Модель",
        "speed": "Швидкість кГц",
        "language": "Мова",
        "theme": "Тема",
        "theme_dark": "Чорна",
        "theme_light": "Біла",
        "idle": "Очікування",
        "running": "Виконується",
        "busy_title": "Зайнято",
        "busy_text": "Вже виконується інший крок.",
        "missing_script": "Скрипт не знайдено",
        "step_locked_title": "Крок заблоковано",
        "already_done_title": "Вже виконано",
        "confirm_title": "Підтвердження",
        "confirm_text": "Цей крок записує дані у пристрій або змінює захист. Продовжити?",
        "spi_exists_title": "Резервна копія SPI вже є",
        "spi_exists_text": "Повний SPI backup вже існує. Скрипт не буде його перезаписувати.",
        "payload_mode_title": "Режим службового завантаження",
        "payload_mode_text": "Payload вже записано у SPI.\n\nЗроби зараз:\n1. Вимкни живлення пристрою.\n2. Подай живлення знову.\n3. Затисни кнопку Power.\n4. Дочекайся синього екрана.\n5. Якщо екран не синій, один раз натисни Time.\n6. Продовжуй тримати Power і натисни Так тут.\n\nПродовжуй тільки коли синій екран видно.",
        "payload_programmed_title": "Payload записано",
        "payload_programmed_text": "Payload записано у SPI.\n\nТепер:\n1. Вимкни живлення пристрою.\n2. Подай живлення знову.\n3. Затисни кнопку Power.\n4. Дочекайся синього екрана.\n5. Якщо екран не синій, один раз натисни Time.\n6. Запусти Step 3 знову, продовжуючи тримати Power.",
        "root_line": "Папка GWUnlock",
        "independent_line": "Локальний інструмент обслуговування пристрою.",
        "result_ok": "Результат: OK",
        "result_failed": "Результат: ПОМИЛКА",
        "full_log": "Повний лог",
        "protection_unlocked": "Захист: ЗНЯТО",
        "protection_locked": "Захист: LOCKED",
        "protection_unknown": "Захист: не перевірено",
        "spi_ok": "Резервна копія SPI: OK",
        "spi_missing": "Резервна копія SPI: немає",
        "internal_ok": "Резервна копія MCU: OK",
        "internal_wait": "Резервна копія MCU: очікується синій екран",
        "internal_invalid": "Резервна копія MCU: неправильна",
        "internal_missing": "Резервна копія MCU: немає",
        "unlock_done": "Розблокування: виконано",
        "unlock_not_done": "Розблокування: не виконано",
        "restore_done": "Відновлення: виконано",
        "restore_not_done": "Відновлення: не виконано",
        "disabled_unlocked": "Цю консоль вже розблоковано. Доступне тільки відновлення за наявності резервних копій.",
        "disabled_generic": "Цей крок вимкнено поточним станом.",
        "already_1": "Перевірку вже позначено OK. Запустити знову?",
        "already_2": "Повний SPI backup вже є. Запустити знову?",
        "already_3": "Валідний internal backup вже є. Запустити знову?",
        "already_4": "Розблокування вже позначено виконаним. Запустити знову?",
        "already_5": "Відновлення вже позначено виконаним. Запустити знову?",
        "step_1": "1. Перевірка захисту",
        "step_2": "2. Копія SPI flash",
        "step_3": "3. Копія пам'яті MCU",
        "step_4": "4. Розблокування",
        "step_5": "5. Відновлення",
        "instr_1": "Перевіряє локальні інструменти і показує стан захисту.",
        "instr_2": "Створює SPI backup. Чекай, доки одна смуга прогресу дійде до 100%.",
        "instr_3_phase2": "Фаза 2: передьорни живлення, затисни Power, дочекайся синього екрана, підтвердь і продовжуй тримати Power.",
        "instr_3_phase1": "Фаза 1: пише payload у SPI. Якщо помилка, передьорни живлення і один раз натисни Power, не тримай, потім повтори.",
        "instr_4": "Розблокування стирає внутрішню пам'ять MCU. Після OK передьорни живлення і запусти крок 5.",
        "instr_5": "Відновлює SPI та внутрішню пам'ять MCU з резервних копій. Після OK передьорни живлення пристрою.",
        "success_4": "OK: пристрій розблоковано. Передьорни живлення, потім запусти крок 5.",
        "success_5": "OK: відновлення завершено. Передьорни живлення пристрою.",
        "success_3_payload": "OK: payload записано. Зроби процедуру синього екрана і знову запусти Step 3.",
        "success_generic": "OK: крок виконано.",
        "fail_3": "ПОМИЛКА: виконай показані дії відновлення і повтори Step 3.",
        "fail_5": "ПОМИЛКА: відновлення не завершено. Дивись подробиці нижче.",
        "fail_generic": "ПОМИЛКА: дивись повний лог нижче.",
        "running_step": "Виконується",
        "payload_write": "Запис payload",
        "payload_programmed": "Payload записано",
        "spi_read": "Читання SPI",
        "spi_write": "Запис SPI",
        "spi_verify": "Перевірка SPI",
        "waiting_data": "очікування даних",
        "step_active": "Крок активний",
        "log": "лог",
        "estimated": "оцінка",
        "yes": "Так",
        "no": "Ні",
        "backup_rotated": "Попередній SPI backup перейменовано",
        "backup_warning": "Важливо: збережи папку backups у безпечному місці. Для відновлення потрібні SPI backup, MCU backup та ITCM backup цієї ж консолі.",
        "need_internal_backup": "Спочатку повністю заверши крок 3 та отримай зелений статус MCU backup.",
        "continue": "Далі",
        "step3_continue": "Payload записано. Вимкни та знову подай живлення, затисни Power, дочекайся синього екрана. Не відпускаючи Power, натисни «Далі».",
        "already_unlocked_with_backup": "Цю консоль вже розблоковано. Резервні копії знайдено, доступне тільки відновлення.",
        "already_unlocked_no_backup": "Цю консоль вже розблоковано. Резервні копії не знайдено, відновлення недоступне.",
        "driver_title": "Потрібен драйвер програматора",
        "driver_text": "Windows виявила програматор, але драйвер працює неправильно.\n\nВідкрити офіційну сторінку встановлення драйвера?",
        "sha_line": "SHA256 програми",
        "auto_read_after_unlock": "Розблокування завершено. Автоматично перечитую інформацію пристрою...",
    },
    "en": {
        "language_name": "English",
        "adapter": "Adapter",
        "target": "Model",
        "speed": "Speed kHz",
        "language": "Language",
        "theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "idle": "Idle",
        "running": "Running",
        "busy_title": "Busy",
        "busy_text": "Another step is already running.",
        "missing_script": "Script not found",
        "step_locked_title": "Step locked",
        "already_done_title": "Already completed",
        "confirm_title": "Confirmation",
        "confirm_text": "This step writes data to the device or changes protection. Continue?",
        "spi_exists_title": "SPI backup exists",
        "spi_exists_text": "A complete SPI backup already exists and will not be overwritten.",
        "payload_mode_title": "Payload mode",
        "payload_mode_text": "The payload is already in SPI.",
        "payload_programmed_title": "Payload programmed",
        "payload_programmed_text": "Power-cycle the device, hold Power, wait for the blue screen, then run Step 3 again.",
        "root_line": "GWUnlock folder",
        "independent_line": "Local device service utility.",
        "result_ok": "Result: OK",
        "result_failed": "Result: ERROR",
        "full_log": "Full log",
        "protection_unlocked": "Protection: UNLOCKED",
        "protection_locked": "Protection: LOCKED",
        "protection_unknown": "Protection: not checked",
        "spi_ok": "SPI backup: OK",
        "spi_missing": "SPI backup: missing",
        "internal_ok": "Internal backup: OK",
        "internal_wait": "Internal backup: waiting for blue-screen phase",
        "internal_invalid": "Internal backup: invalid",
        "internal_missing": "Internal backup: missing",
        "unlock_done": "Unlock: completed",
        "unlock_not_done": "Unlock: not completed",
        "restore_done": "Restore: completed",
        "restore_not_done": "Restore: not completed",
        "disabled_unlocked": "The device is already unlocked. Run Step 5 Restore; other steps are disabled.",
        "disabled_generic": "This step is disabled by the current state.",
        "already_1": "The check is already marked OK. Run it again?",
        "already_2": "A complete SPI backup already exists. Run it again?",
        "already_3": "A valid internal backup already exists. Run it again?",
        "already_4": "Unlock is already marked completed. Run it again?",
        "already_5": "Restore is already marked completed. Run it again?",
        "step_1": "1. Check protection",
        "step_2": "2. Backup SPI flash",
        "step_3": "3. Backup internal flash",
        "step_4": "4. Unlock device",
        "step_5": "5. Restore backup",
        "instr_1": "Checks local tools, detects the model, and reads protection status.",
        "instr_2": "Creates an SPI backup. Wait for the progress bar to reach 100%.",
        "instr_3_phase2": "Phase 2: power-cycle, hold Power, wait for the blue screen, confirm, and keep holding Power.",
        "instr_3_phase1": "Phase 1: programs a 64 MiB payload image to SPI. This may take several minutes.",
        "instr_4": "Unlock erases internal flash. After OK, power-cycle and run Step 5 Restore.",
        "instr_5": "Restores SPI and internal flash from backup. Power-cycle after completion.",
        "success_4": "OK: device unlocked. Power-cycle it, then run Step 5 Restore.",
        "success_5": "OK: restore completed. Power-cycle the device.",
        "success_3_payload": "OK: payload programmed. Perform the blue-screen procedure and run Step 3 again.",
        "success_generic": "OK: step completed.",
        "fail_3": "ERROR: follow the displayed recovery instructions and repeat Step 3.",
        "fail_5": "ERROR: restore did not complete. See the details below.",
        "fail_generic": "ERROR: see the details below.",
        "running_step": "Running",
        "payload_write": "Programming payload",
        "payload_programmed": "Payload programmed",
        "spi_read": "Reading SPI",
        "spi_write": "Writing SPI",
        "spi_verify": "Verifying SPI",
        "waiting_data": "waiting for data",
        "step_active": "Step active",
        "log": "log",
        "estimated": "estimated",
        "yes": "Yes",
        "no": "No",
        "backup_rotated": "Previous SPI backup renamed",
        "backup_warning": "Important: keep the backups folder in a safe place. Restore needs the SPI backup, MCU backup, and ITCM backup from this same device.",
        "need_internal_backup": "Complete Step 3 and obtain a green MCU backup status first.",
        "continue": "Continue",
        "step3_continue": "Payload programmed. Power-cycle the device, hold Power, and wait for the blue screen. Keep holding Power and click Continue.",
        "already_unlocked_with_backup": "This device is already unlocked. Backups were found; only restore is available.",
        "already_unlocked_no_backup": "This device is already unlocked. Backups were not found; restore is unavailable.",
        "driver_title": "Debug probe driver required",
        "driver_text": "Windows detected the debug probe, but its driver is not working correctly.\n\nOpen the official driver installation page?",
        "sha_line": "Program SHA256",
        "auto_read_after_unlock": "Unlock completed. Reading device information automatically...",
    },
}


class StepWorker(QThread):
    line = Signal(str)
    finished_code = Signal(int)

    def __init__(self, command: list[str], env: dict[str, str]) -> None:
        super().__init__()
        self.command = command
        self.env = env

    def run(self) -> None:
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            process = subprocess.Popen(
                self.command,
                cwd=str(ROOT),
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
            assert process.stdout is not None
            for output_line in process.stdout:
                self.line.emit(output_line.rstrip())
            self.finished_code.emit(process.wait())
        except Exception as exc:
            self.line.emit(f"ERROR: {exc}")
            self.finished_code.emit(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        prepare_runtime()
        self.worker: StepWorker | None = None
        self.current_script = ""
        self.progress_start = 0.0
        self.phase_start = 0.0
        self.step3_estimated_stage = ""
        self.last_progress_size = -1
        self.last_log_size = 0
        self.buttons: dict[str, QPushButton] = {}
        self.step_raw_lines: list[str] = []
        self.lang = detect_default_language()
        self.dark_theme = True
        self.pending_backup_restart = False
        self.protection_status: str | None = None

        self.setWindowTitle("GWUnlock")
        if APP_ICON.exists():
            self.setWindowIcon(QIcon(str(APP_ICON)))
        self.resize(920, 640)
        self.setMinimumSize(780, 520)

        self.adapter = QComboBox()
        self.adapter.addItems(["auto", "stlink", "jlink", "cmsis-dap"])

        self.target = QComboBox()
        self.target.addItems(["mario", "zelda"])
        if (STATE / "model_zelda.ok").exists():
            self.target.setCurrentText("zelda")
        self.target.setToolTip(
            "Mario и Zelda используют разные смещения SPI/ITCM и разные контрольные суммы."
        )

        self.speed = QComboBox()
        self.speed.setEditable(True)
        self.speed.addItems(["8000", "4000", "2000", "1000", "500", "200", "100"])
        self.language = QComboBox()
        self.language.addItem(LANGS["ru"]["language_name"], "ru")
        self.language.addItem(LANGS["uk"]["language_name"], "uk")
        self.language.addItem(LANGS["en"]["language_name"], "en")
        index = self.language.findData(self.lang)
        if index >= 0:
            self.language.setCurrentIndex(index)
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.toggle_theme)
        self.status = QLabel(self.tr("idle"))
        self.progress = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.state_label = QLabel("")
        self.instructions = QLabel("")
        self.instructions.setWordWrap(True)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.history_path = APP_ROOT / f"GWUnlock_{datetime.now():%Y%m%d_%H%M%S}.log"
        self.exe_sha256 = current_program_sha256()
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(3000)
        self.progress_timer.timeout.connect(self.poll_progress)
        self.state_timer = QTimer(self)
        self.state_timer.setInterval(5000)
        self.state_timer.timeout.connect(self.refresh_state)

        root = QWidget()
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        self.adapter_label = QLabel()
        self.target_label = QLabel()
        self.speed_label = QLabel()
        self.language_label = QLabel("Language")
        self.theme_label = QLabel()
        top.addWidget(self.adapter_label)
        top.addWidget(self.adapter)
        top.addWidget(self.target_label)
        top.addWidget(self.target)
        top.addWidget(self.speed_label)
        top.addWidget(self.speed)
        top.addWidget(self.language_label)
        top.addWidget(self.language)
        top.addWidget(self.theme_label)
        top.addWidget(self.theme_button)
        top.addStretch(1)
        top.addWidget(self.status)
        layout.addLayout(top)
        layout.addWidget(self.state_label)
        self.sha_label = QLabel("")
        self.sha_label.setWordWrap(True)
        layout.addWidget(self.sha_label)
        layout.addWidget(self.instructions)
        confirmation = QHBoxLayout()
        self.confirm_yes = QPushButton()
        self.confirm_no = QPushButton()
        self.step3_continue = QPushButton()
        self.confirm_yes.clicked.connect(self.confirm_backup_restart)
        self.confirm_no.clicked.connect(self.cancel_confirmation)
        self.step3_continue.clicked.connect(self.continue_step3)
        self.confirm_yes.setVisible(False)
        self.confirm_no.setVisible(False)
        self.step3_continue.setVisible(False)
        confirmation.addWidget(self.confirm_yes)
        confirmation.addWidget(self.confirm_no)
        confirmation.addWidget(self.step3_continue)
        confirmation.addStretch(1)
        layout.addLayout(confirmation)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        for script_name, label, destructive in STEP_DEFS:
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, s=script_name, d=destructive: self.run_step(s, d)
            )
            buttons.addWidget(button)
            self.buttons[script_name] = button
        layout.addLayout(buttons)
        layout.addWidget(self.output, 1)

        self.setCentralWidget(root)
        self.language.currentIndexChanged.connect(self.on_language_changed)
        self.apply_theme()
        self.retranslate_static_ui()
        self.append(f"{self.tr('root_line')}: {ROOT}")
        self.append(f"{self.tr('sha_line')}: {self.exe_sha256}")
        self.append(self.tr("independent_line"))
        self.target.currentTextChanged.connect(self.on_target_changed)
        self.refresh_state()
        self.state_timer.start()
        QTimer.singleShot(500, self.check_driver_status)

    def tr(self, key: str) -> str:
        return LANGS[self.lang].get(key, LANGS["ru"].get(key, key))

    def on_language_changed(self) -> None:
        self.lang = self.language.currentData() or "ru"
        self.retranslate_static_ui()
        self.refresh_state()
        if self.current_script:
            self.instructions.setText(self.step_instruction_text(self.current_script))

    def toggle_theme(self) -> None:
        self.dark_theme = not self.dark_theme
        self.apply_theme()
        self.retranslate_static_ui()
        self.refresh_state()

    def apply_theme(self) -> None:
        if self.dark_theme:
            self.setStyleSheet("""
                QWidget { background: #202020; color: #f2f2f2; }
                QTextEdit, QComboBox { background: #2c2c2c; color: #ffffff; border: 1px solid #4b4b4b; border-radius: 4px; padding: 3px; }
                QPushButton { background: #2b2b2b; color: #ffffff; border: 1px solid #555; border-radius: 5px; padding: 5px; }
                QPushButton:hover { background: #383838; }
                QPushButton:disabled { color: #777; background: #242424; }
                QProgressBar { border: 1px solid #666; border-radius: 3px; text-align: right; }
                QProgressBar::chunk { background-color: #26aeea; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background: #f6f6f2; color: #171717; }
                QTextEdit, QComboBox { background: #ffffff; color: #111111; border: 1px solid #b8b8b0; border-radius: 4px; padding: 3px; }
                QPushButton { background: #eeeeea; color: #111111; border: 1px solid #b5b5ad; border-radius: 5px; padding: 5px; }
                QPushButton:hover { background: #e2e2dc; }
                QPushButton:disabled { color: #999; background: #eeeeee; }
                QProgressBar { border: 1px solid #9a9a92; border-radius: 3px; text-align: right; }
                QProgressBar::chunk { background-color: #0078d4; }
            """)

    def on_target_changed(self) -> None:
        if self.current_script != "1_sanity_check.cmd":
            self.protection_status = None
        self.refresh_state()

    def retranslate_static_ui(self) -> None:
        self.adapter_label.setText(self.tr("adapter"))
        self.target_label.setText(self.tr("target"))
        self.speed_label.setText(self.tr("speed"))
        self.language_label.setText(self.tr("language"))
        self.theme_label.setText(self.tr("theme"))
        self.theme_button.setText(self.tr("theme_light") if self.dark_theme else self.tr("theme_dark"))
        self.confirm_yes.setText(self.tr("yes"))
        self.confirm_no.setText(self.tr("no"))
        self.step3_continue.setText(self.tr("continue"))
        self.sha_label.setText(f"{self.tr('sha_line')}: {self.exe_sha256}")
        tooltips = {
            "ru": "Mario и Zelda используют разные смещения SPI/ITCM и разные контрольные суммы.",
            "uk": "Mario і Zelda використовують різні зміщення SPI/ITCM та різні контрольні суми.",
            "en": "Mario and Zelda use different SPI/ITCM offsets and checksums.",
        }
        self.target.setToolTip(tooltips[self.lang])
        if self.status.text() in ("Idle", "Ожидание", "Очікування"):
            self.status.setText(self.tr("idle"))
        state = self.current_state()
        if state["payload_pending"] and not state["internal_backup"]:
            self.instructions.setText(self.tr("step3_continue"))

    def check_driver_status(self) -> None:
        command = (
            "$devices=Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | "
            "Where-Object {$_.InstanceId -match 'VID_0483|VID_1366|VID_0D28'}; "
            "foreach($d in $devices){"
            "$vendor=if($d.InstanceId -match 'VID_1366'){'jlink'}"
            "elseif($d.InstanceId -match 'VID_0D28'){'cmsis-dap'}else{'stlink'};"
            "Write-Output ($vendor+'|'+$d.Status+'|'+$d.FriendlyName)}"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return
        problem = next(
            (
                line.split("|", 2)[0]
                for line in result.stdout.splitlines()
                if "|" in line and line.split("|", 2)[1].strip().upper() != "OK"
            ),
            "",
        )
        if not problem:
            return
        answer = QMessageBox.question(
            self,
            self.tr("driver_title"),
            self.tr("driver_text"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        links = {
            "stlink": "https://www.st.com/en/development-tools/stsw-link009.html",
            "jlink": "https://www.segger.com/downloads/jlink/",
            "cmsis-dap": "https://pyocd.io/docs/debug_probes.html#cmsis-dap",
        }
        webbrowser.open(links.get(problem, links["cmsis-dap"]))

    def append(self, text: str) -> None:
        self.step_raw_lines.append(text)
        try:
            with self.history_path.open("a", encoding="utf-8") as history:
                history.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n")
        except OSError:
            pass
        if text == "Protection: UNLOCKED":
            self.protection_status = "unlocked"
        elif text in ("Protection: LOCKED", "Protection: LEVEL2"):
            self.protection_status = "locked"
        elif text == "Protection: UNKNOWN":
            self.protection_status = "unknown"
        if text.startswith("GNW_READ_PROGRESS ") or text.startswith("GNW_WRITE_PROGRESS ") or text.startswith("GNW_VERIFY_PROGRESS "):
            self.handle_gnw_progress(text)
            return
        elif text.startswith("[stage] payload_write"):
            self.step3_estimated_stage = "payload_write"
            self.phase_start = time.monotonic()
            self.progress_bar.setRange(0, 0)
            self.progress.setText(f"{self.tr('payload_write')}: 0s")
        elif text.startswith("[stage] payload_done"):
            self.step3_estimated_stage = ""
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.progress.setText(self.tr("payload_programmed"))
        elif text.startswith("Detected model: "):
            detected = text.partition(":")[2].strip().lower()
            if detected in ("mario", "zelda") and detected != self.target.currentText():
                self.target.setCurrentText(detected)
            if detected in ("mario", "zelda"):
                self.output.append(self.clean_line(text))
            return
        elif text.startswith("[phase] "):
            self.progress.setText(self.translate_phase(text.removeprefix("[phase] ").strip()))
        if self.should_show_line(text):
            self.output.append(self.clean_line(text))

    def should_show_line(self, text: str) -> bool:
        if not text.strip():
            return True
        hidden_prefixes = (
            "CONFIG ",
            "> cmd.exe",
            "settings:",
            "[openocd]",
            "GNW_",
            "SHA1 mismatch",
            "expected ",
            "actual   ",
        )
        if text.startswith(hidden_prefixes):
            return False
        important = (
            "Protection:",
            "Detected model:",
            "Running sanity checks",
            "Looks good",
            "Already have",
            "Attempting",
            "Dumping",
            "Successfully",
            "Payload",
            "Flash successfully",
            "Device backed up successfully",
            "Official internal",
            "Internal backup accepted",
            "Validating",
            "Unlocking device",
            "Device unlocked",
            "Restoring",
            "Restore source",
            "Restore config",
            "Restore openocd",
            "Restore scripts",
            "Restore SPI address",
            "Restore MCU address",
            "Restore completed",
            "MCU readback",
            "SPI_SOURCE",
            "MCU_SOURCE",
            "MCU_READBACK",
            "MCU_COMPARE",
            "STM32 vector OK",
            "Internal flash image OK",
            "Exit code:",
            "ERROR:",
            "failed",
            "Failed",
            "Backup is not valid",
            "No backup",
            "Recovery procedure",
            "WARNING:",
            "- ",
        )
        return text.startswith(important) or "successfully" in text.lower()

    def clean_line(self, text: str) -> str:
        if text.startswith("Detected model: "):
            model = text.partition(":")[2].strip()
            if self.lang == "ru":
                return f"Определена модель: {model}"
            if self.lang == "uk":
                return f"Визначено модель: {model}"
            return text
        if text.startswith("Exit code: 0"):
            return self.tr("result_ok")
        if text.startswith("Exit code:"):
            return self.tr("result_failed")
        dynamic = self.translate_dynamic_line(text)
        if dynamic != text:
            return dynamic
        translations = {
            "Running sanity checks...": {
                "ru": "Проверка инструментов...",
                "uk": "Перевірка інструментів...",
            },
            "Looks good.": {
                "ru": "Проверка OK.",
                "uk": "Перевірка OK.",
            },
            "Protection: UNLOCKED": {
                "ru": "Защита: СНЯТА",
                "uk": "Захист: ЗНЯТО",
            },
            "Protection: LOCKED": {
                "ru": "Защита: LOCKED",
                "uk": "Захист: LOCKED",
            },
            "Protection: LOCKED_OR_UNKNOWN": {
                "ru": "Защита: LOCKED",
                "uk": "Захист: LOCKED",
                "en": "Protection: LOCKED",
            },
            "Protection: UNKNOWN": {
                "ru": "Защита: UNKNOWN",
                "uk": "Захист: UNKNOWN",
            },
            "Restore completed. Power-cycle the device.": {
                "ru": "Восстановление завершено. Передёрни питание устройства.",
                "uk": "Відновлення завершено. Передьорни живлення пристрою.",
            },
            "Device unlocked. Power-cycle the device, then run restore.": {
                "ru": "Устройство разблокировано. Передёрни питание, затем запусти восстановление.",
                "uk": "Пристрій розблоковано. Передьорни живлення, потім запусти відновлення.",
            },
            "Device backed up successfully.": {
                "ru": "Резервная копия устройства создана.",
                "uk": "Резервну копію пристрою створено.",
            },
            "Generating encrypted flash image from backed up data...": {
                "ru": "Создание зашифрованного payload из резервной копии...",
                "uk": "Створення зашифрованого payload із резервної копії...",
            },
            "Validating ITCM dump...": {
                "ru": "Проверка ITCM...",
                "uk": "Перевірка ITCM...",
            },
            "Validating SPI checksum...": {
                "ru": "Проверка контрольной суммы SPI...",
                "uk": "Перевірка контрольної суми SPI...",
            },
            "Recovery procedure:": {
                "ru": "Действия для восстановления:",
                "uk": "Дії для відновлення:",
            },
            "IMPORTANT: keep the backups folder safe. Restore needs SPI, MCU, and ITCM backups from this device.": {
                "ru": "ВАЖНО: сохрани папку backups в безопасном месте. Для восстановления нужны SPI, MCU и ITCM backup этой консоли.",
                "uk": "ВАЖЛИВО: збережи папку backups у безпечному місці. Для відновлення потрібні SPI, MCU та ITCM backup цієї консолі.",
            },
            "- Disconnect and reconnect power": {
                "ru": "- Отключи и снова подключи питание.",
                "uk": "- Вимкни та знову підключи живлення.",
            },
            "- Press the Power button once": {
                "ru": "- Один раз нажми Power.",
                "uk": "- Один раз натисни Power.",
            },
            "- Do not hold the Power button at this stage": {
                "ru": "- На этом этапе не удерживай Power.",
                "uk": "- На цьому етапі не утримуй Power.",
            },
            "- Run Step 3 again": {
                "ru": "- Повтори шаг 3.",
                "uk": "- Повтори крок 3.",
            },
            "Flash successfully programmed. Now do the following procedure:": {
                "ru": "Payload успешно записан. Выполни следующую процедуру:",
                "uk": "Payload успішно записано. Виконай наступну процедуру:",
            },
            "- Disconnect power from the device": {
                "ru": "- Отключи питание устройства.",
                "uk": "- Вимкни живлення пристрою.",
            },
            "- Power it again": {
                "ru": "- Снова подай питание.",
                "uk": "- Знову подай живлення.",
            },
            "- Press and hold the power button on the device": {
                "ru": "- Зажми и удерживай кнопку Power.",
                "uk": "- Затисни та утримуй кнопку Power.",
            },
            "- The LCD should show a blue screen": {
                "ru": "- На экране должен появиться синий фон.",
                "uk": "- На екрані має з'явитися синій фон.",
            },
            "- If it is not blue, try pressing the Time button on the device": {
                "ru": "- Если экран не синий, один раз нажми Time.",
                "uk": "- Якщо екран не синій, один раз натисни Time.",
            },
            "- Then press Step 3 again in this tool while still holding the power button": {
                "ru": "- Не отпуская Power, снова нажми шаг 3.",
                "uk": "- Не відпускаючи Power, знову натисни крок 3.",
            },
        }
        if text in translations:
            return translations[text].get(self.lang, text)
        return text

    def translate_dynamic_line(self, text: str) -> str:
        if self.lang == "en":
            return text
        mappings = {
            "ru": (
                ("Restore source SPI:", "Источник восстановления SPI:"),
                ("Restore source MCU:", "Источник восстановления MCU:"),
                ("Restore config ", "Параметры восстановления "),
                ("Restore openocd=", "OpenOCD для восстановления="),
                ("Restore scripts=", "Скрипты OpenOCD="),
                ("Restore SPI address=", "Адрес восстановления SPI="),
                ("Restore MCU address=", "Адрес восстановления MCU="),
                ("Restoring SPI flash through GNWManager helper...", "Восстановление SPI flash через GNWManager..."),
                ("Restoring internal flash ", "Восстановление внутренней памяти MCU "),
                ("MCU readback address=", "Контрольное чтение MCU, адрес="),
                ("MCU readback verification failed.", "Контрольное чтение MCU не совпало."),
                ("MCU readback does not match backup.", "Считанные данные MCU не совпадают с резервной копией."),
                ("Programming payload to SPI flash...", "Запись служебного образа во SPI..."),
                ("Writing payload to SPI flash failed.", "Не удалось записать служебный образ во SPI."),
                ("Payload image exists", "Служебный образ уже существует"),
                ("Extracting checksummed SPI range...", "Извлечение проверяемой области SPI..."),
                ("Dumping ITCM bootstrap area", "Чтение загрузочной области ITCM"),
                ("Valid ITCM backup is missing", "Валидный ITCM backup отсутствует"),
                ("Run Step 2 on a stock booting device first.", "Сначала выполни шаг 2 на штатно запускающейся консоли."),
                ("Run Step 2 again", "Повтори шаг 2"),
                ("ITCM read attempt ", "Попытка чтения ITCM "),
                ("Existing ITCM backup is valid.", "Существующая резервная копия ITCM корректна."),
                ("Existing SPI backup is incomplete:", "Существующая резервная копия SPI неполная:"),
                ("Existing internal flash backup is invalid.", "Существующая резервная копия MCU некорректна."),
                ("Removing stale payload image", "Удаление незавершённого служебного образа"),
                ("SPI backup is missing.", "Резервная копия SPI отсутствует."),
                ("SPI backup has unexpected size:", "Неверный размер резервной копии SPI:"),
                ("Internal flash backup is missing.", "Резервная копия MCU отсутствует."),
                ("Backup is not valid.", "Резервная копия некорректна."),
                ("The backup of the internal flash failed.", "Не удалось создать резервную копию MCU."),
                ("Second internal flash dump failed.", "Повторное чтение MCU завершилось ошибкой."),
                ("Dumping internal flash second pass...", "Повторное чтение внутренней памяти MCU..."),
                ("Already have valid ", "Корректная резервная копия уже существует: "),
                ("Already have stable custom ", "Стабильная резервная копия уже существует: "),
                ("Already have complete ", "Полная резервная копия уже существует: "),
                ("Already have ", "Резервная копия уже существует: "),
                ("Close other programmer/debugger applications", "Закрой другие программы программатора и отладчика"),
                ("ST-Link is busy:", "ST-Link занят:"),
                ("OpenOCD does not seem to be working.", "OpenOCD не работает."),
                ("Python does not seem to be working.", "Python не работает."),
                ("Cannot find openocd.exe.", "Не найден openocd.exe."),
                ("Cannot find Python.", "Не найден Python."),
                ("Missing adapter config:", "Отсутствует конфигурация адаптера:"),
                ("Missing target config:", "Отсутствует конфигурация устройства:"),
                ("Missing unlock config:", "Отсутствует конфигурация разблокировки:"),
                ("Missing payload", "Отсутствует служебный образ"),
                ("ERROR:", "ОШИБКА:"),
                ("Attempting to dump SPI flash", "Начало чтения SPI flash"),
                ("Dumping 64 MiB SPI flash", "Чтение 64 МиБ SPI flash"),
                ("Successfully backed up 64 MiB SPI flash", "Резервная копия 64 МиБ SPI flash создана"),
                ("Dumping internal flash...", "Чтение внутренней памяти MCU..."),
                ("Verifying internal flash backup...", "Проверка резервной копии MCU..."),
                ("Validating internal flash backup before unlock...", "Проверка резервной копии MCU перед разблокировкой..."),
                ("Unlocking device.", "Разблокировка устройства."),
                ("Device unlocked.", "Устройство разблокировано."),
                ("Official internal flash SHA1 mismatch.", "Официальная SHA1 внутренней памяти не совпала."),
                ("Internal backup accepted", "Резервная копия MCU принята"),
                ("STM32 vector OK:", "Таблица векторов STM32 корректна:"),
                ("Internal flash image OK:", "Образ внутренней памяти корректен:"),
                ("WARNING:", "ПРЕДУПРЕЖДЕНИЕ:"),
                ("Failed ", "Ошибка: "),
                ("No backup ", "Резервная копия отсутствует: "),
            ),
            "uk": (
                ("Restore source SPI:", "Джерело відновлення SPI:"),
                ("Restore source MCU:", "Джерело відновлення MCU:"),
                ("Restore config ", "Параметри відновлення "),
                ("Restore openocd=", "OpenOCD для відновлення="),
                ("Restore scripts=", "Скрипти OpenOCD="),
                ("Restore SPI address=", "Адреса відновлення SPI="),
                ("Restore MCU address=", "Адреса відновлення MCU="),
                ("Restoring SPI flash through GNWManager helper...", "Відновлення SPI flash через GNWManager..."),
                ("Restoring internal flash ", "Відновлення внутрішньої пам'яті MCU "),
                ("MCU readback address=", "Контрольне читання MCU, адреса="),
                ("MCU readback verification failed.", "Контрольне читання MCU не збіглося."),
                ("MCU readback does not match backup.", "Прочитані дані MCU не збігаються з резервною копією."),
                ("Programming payload to SPI flash...", "Запис службового образу у SPI..."),
                ("Writing payload to SPI flash failed.", "Не вдалося записати службовий образ у SPI."),
                ("Payload image exists", "Службовий образ вже існує"),
                ("Extracting checksummed SPI range...", "Виділення контрольованої області SPI..."),
                ("Dumping ITCM bootstrap area", "Читання завантажувальної області ITCM"),
                ("Valid ITCM backup is missing", "Валідний ITCM backup відсутній"),
                ("Run Step 2 on a stock booting device first.", "Спочатку виконай крок 2 на штатно завантажуваній консолі."),
                ("Run Step 2 again", "Повтори крок 2"),
                ("ITCM read attempt ", "Спроба читання ITCM "),
                ("Existing ITCM backup is valid.", "Наявна резервна копія ITCM коректна."),
                ("Existing SPI backup is incomplete:", "Наявна резервна копія SPI неповна:"),
                ("Existing internal flash backup is invalid.", "Наявна резервна копія MCU некоректна."),
                ("Removing stale payload image", "Видалення незавершеного службового образу"),
                ("SPI backup is missing.", "Резервна копія SPI відсутня."),
                ("SPI backup has unexpected size:", "Неправильний розмір резервної копії SPI:"),
                ("Internal flash backup is missing.", "Резервна копія MCU відсутня."),
                ("Backup is not valid.", "Резервна копія некоректна."),
                ("The backup of the internal flash failed.", "Не вдалося створити резервну копію MCU."),
                ("Second internal flash dump failed.", "Повторне читання MCU завершилося помилкою."),
                ("Dumping internal flash second pass...", "Повторне читання внутрішньої пам'яті MCU..."),
                ("Already have valid ", "Коректна резервна копія вже існує: "),
                ("Already have stable custom ", "Стабільна резервна копія вже існує: "),
                ("Already have complete ", "Повна резервна копія вже існує: "),
                ("Already have ", "Резервна копія вже існує: "),
                ("Close other programmer/debugger applications", "Закрий інші програми програматора та відлагоджувача"),
                ("ST-Link is busy:", "ST-Link зайнятий:"),
                ("OpenOCD does not seem to be working.", "OpenOCD не працює."),
                ("Python does not seem to be working.", "Python не працює."),
                ("Cannot find openocd.exe.", "Не знайдено openocd.exe."),
                ("Cannot find Python.", "Не знайдено Python."),
                ("Missing adapter config:", "Відсутня конфігурація адаптера:"),
                ("Missing target config:", "Відсутня конфігурація пристрою:"),
                ("Missing unlock config:", "Відсутня конфігурація розблокування:"),
                ("Missing payload", "Відсутній службовий образ"),
                ("ERROR:", "ПОМИЛКА:"),
                ("Attempting to dump SPI flash", "Початок читання SPI flash"),
                ("Dumping 64 MiB SPI flash", "Читання 64 МіБ SPI flash"),
                ("Successfully backed up 64 MiB SPI flash", "Резервну копію 64 МіБ SPI flash створено"),
                ("Dumping internal flash...", "Читання внутрішньої пам'яті MCU..."),
                ("Verifying internal flash backup...", "Перевірка резервної копії MCU..."),
                ("Validating internal flash backup before unlock...", "Перевірка резервної копії MCU перед розблокуванням..."),
                ("Unlocking device.", "Розблокування пристрою."),
                ("Device unlocked.", "Пристрій розблоковано."),
                ("Official internal flash SHA1 mismatch.", "Офіційна SHA1 внутрішньої пам'яті не збігається."),
                ("Internal backup accepted", "Резервну копію MCU прийнято"),
                ("STM32 vector OK:", "Таблиця векторів STM32 коректна:"),
                ("Internal flash image OK:", "Образ внутрішньої пам'яті коректний:"),
                ("WARNING:", "ПОПЕРЕДЖЕННЯ:"),
                ("Failed ", "Помилка: "),
                ("No backup ", "Резервна копія відсутня: "),
            ),
        }
        for source, translated in mappings[self.lang]:
            if text.startswith(source):
                text = translated + text[len(source):]
                break
        suffixes = {
            "ru": {
                "Check logs\\2_openocd.log.": "Подробности показаны ниже.",
                "Check logs\\3_openocd.log.": "Подробности показаны ниже.",
                "Check logs\\4_openocd.log.": "Подробности показаны ниже.",
                "Check logs\\5_openocd.log.": "Подробности показаны ниже.",
                "refusing to overwrite.": "перезапись отменена.",
                "Run Step 2 first.": "Сначала выполни шаг 2.",
                "Restore cancelled.": "Восстановление отменено.",
            },
            "uk": {
                "Check logs\\2_openocd.log.": "Подробиці показано нижче.",
                "Check logs\\3_openocd.log.": "Подробиці показано нижче.",
                "Check logs\\4_openocd.log.": "Подробиці показано нижче.",
                "Check logs\\5_openocd.log.": "Подробиці показано нижче.",
                "refusing to overwrite.": "перезапис скасовано.",
                "Run Step 2 first.": "Спочатку виконай крок 2.",
                "Restore cancelled.": "Відновлення скасовано.",
            },
        }
        for source, translated in suffixes[self.lang].items():
            text = text.replace(source, translated)
        field_names = {
            "ru": {
                " path=": " путь=",
                " size=": " размер=",
                " vector_sp=": " вектор_SP=",
                " vector_pc=": " вектор_PC=",
                " expected_path=": " ожидаемый_путь=",
                " actual_path=": " фактический_путь=",
                " expected_size=": " ожидаемый_размер=",
                " actual_size=": " фактический_размер=",
                " result=MATCH": " результат=СОВПАДАЕТ",
                " result=DIFFER": " результат=НЕ_СОВПАДАЕТ",
            },
            "uk": {
                " path=": " шлях=",
                " size=": " розмір=",
                " vector_sp=": " вектор_SP=",
                " vector_pc=": " вектор_PC=",
                " expected_path=": " очікуваний_шлях=",
                " actual_path=": " фактичний_шлях=",
                " expected_size=": " очікуваний_розмір=",
                " actual_size=": " фактичний_розмір=",
                " result=MATCH": " результат=ЗБІГАЄТЬСЯ",
                " result=DIFFER": " результат=НЕ_ЗБІГАЄТЬСЯ",
            },
        }
        for source, translated in field_names[self.lang].items():
            text = text.replace(source, translated)
        return text

    def translate_phase(self, text: str) -> str:
        phases = {
            "Preparing payload image for internal flash backup.": {
                "ru": "Подготовка payload для чтения MCU.",
                "uk": "Підготовка payload для читання MCU.",
            },
            "Programming 64 MiB payload image to SPI flash. This can take several minutes.": {
                "ru": "Запись payload 64 МиБ во SPI. Это займёт несколько минут.",
                "uk": "Запис payload 64 МіБ у SPI. Це займе кілька хвилин.",
            },
            "Payload mode confirmed. Reading internal flash from SRAM mirror.": {
                "ru": "Синий экран подтверждён. Чтение MCU из SRAM.",
                "uk": "Синій екран підтверджено. Читання MCU із SRAM.",
            },
            "Restoring and verifying SPI flash.": {
                "ru": "Восстановление и проверка SPI.",
                "uk": "Відновлення та перевірка SPI.",
            },
            "Programming and verifying MCU internal flash.": {
                "ru": "Запись и проверка внутренней памяти MCU.",
                "uk": "Запис і перевірка внутрішньої пам'яті MCU.",
            },
            "Reading MCU back for final compare.": {
                "ru": "Контрольное чтение MCU для итоговой проверки.",
                "uk": "Контрольне читання MCU для підсумкової перевірки.",
            },
        }
        return phases.get(text, {}).get(self.lang, text)

    def handle_gnw_progress(self, text: str) -> None:
        parts = text.split()
        if len(parts) < 5:
            return
        kind = parts[0].replace("GNW_", "").replace("_PROGRESS", "").lower()
        try:
            percent = float(parts[1])
            done = int(parts[2])
            total = int(parts[3])
            speed = float(parts[4])
        except ValueError:
            return
        label = self.tr("spi_read") if kind == "read" else self.tr("spi_write") if kind == "write" else self.tr("spi_verify")
        progress = (
            f"{label}: {percent:.0f}% "
            f"{done / (1024 * 1024):.1f}/{total / (1024 * 1024):.1f} MB, "
            f"{speed / (1024 * 1024):.2f} MB/s"
        )
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(max(0, min(percent, 100))))
        self.progress.setText(progress)

    def ask_backup_restart(self) -> None:
        self.pending_backup_restart = True
        self.instructions.setText(self.tr("already_2"))
        self.confirm_yes.setVisible(True)
        self.confirm_no.setVisible(True)

    def cancel_confirmation(self) -> None:
        self.pending_backup_restart = False
        self.confirm_yes.setVisible(False)
        self.confirm_no.setVisible(False)
        self.instructions.setText("")

    def show_step3_continue(self) -> None:
        self.instructions.setText(self.tr("step3_continue"))
        self.step3_continue.setVisible(True)

    def continue_step3(self) -> None:
        state = self.current_state()
        if not state["payload_pending"] or state["internal_backup"]:
            self.step3_continue.setVisible(False)
            self.refresh_state()
            return
        self.step3_continue.setVisible(False)
        self.start_step("3_backup_internal_flash.cmd", True)

    def confirm_backup_restart(self) -> None:
        if not self.pending_backup_restart:
            return
        self.cancel_confirmation()
        target = self.current_target()
        backup = self.backup_path(f"flash_backup_{target}.bin")
        archived_name = ""
        if backup.exists():
            index = 0
            while True:
                suffix = ".old" if index == 0 else f".old{index}"
                archived = backup.with_name(backup.name + suffix)
                if not archived.exists():
                    backup.rename(archived)
                    archived_name = archived.name
                    break
                index += 1
        self.marker_path(f"spi_backup_{target}.ok").unlink(missing_ok=True)
        self.start_step("2_backup_flash.cmd", False)
        if archived_name:
            self.append(f"{self.tr('backup_rotated')}: {archived_name}")

    def run_step(self, script_name: str, destructive: bool) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.instructions.setText(self.tr("busy_text"))
            return

        script_path = STEPS / script_name
        if not script_path.exists():
            self.instructions.setText(f"{self.tr('missing_script')}: {script_path}")
            return

        state = self.current_state()
        if not self.can_run_step(script_name, state):
            self.instructions.setText(self.disabled_reason(script_name, state))
            return
        if script_name == "2_backup_flash.cmd" and state["spi_backup"]:
            self.ask_backup_restart()
            return
        if self.is_step_complete(script_name, state):
            if script_name not in ("1_sanity_check.cmd", "5_restore.cmd"):
                self.instructions.setText(self.completed_message(script_name))
                return

        self.start_step(script_name, destructive)

    def start_step(self, script_name: str, destructive: bool) -> None:
        sync_to_runtime()
        script_path = STEPS / script_name
        self.step3_continue.setVisible(False)
        payload_confirmed = False
        if destructive:
            if script_name == "3_backup_internal_flash.cmd" and self.marker_path(
                f"payload_pending_{self.current_target()}.ok"
            ).exists():
                payload_confirmed = True

        env = os.environ.copy()
        env["GW_SERVICE_ASSUME_YES"] = "1" if destructive else "0"
        env["LARGE_FLASH"] = "1"
        env["GW_SERVICE_SKIP_SPI_SHA1"] = "1"
        env["GW_SERVICE_PAYLOAD_CONFIRMED"] = "1" if payload_confirmed else "0"
        env["OPENOCD_ADAPTER_SPEED"] = self.speed.currentText().strip() or "8000"
        env["GW_SERVICE_BACKUP_DIR"] = str(BACKUPS)
        env["GW_SERVICE_MARKER_DIR"] = str(STATE)
        if FROZEN:
            env["GW_SERVICE_INTERNAL_EXE"] = str(sys.executable)
            env["OPENOCD"] = str(ASSET_ROOT / "vendor" / "openocd" / "bin" / "openocd.exe")
            env["OPENOCD_SCRIPTS"] = str(ASSET_ROOT / "vendor" / "openocd" / "scripts")

        command = [
            "cmd.exe",
            "/c",
            str(script_path),
            self.adapter.currentText(),
            self.target.currentText(),
        ]

        self.step_raw_lines = []
        separator = (
            f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} | "
            f"{self.step_title(script_name)} | {self.current_target()} ====="
        )
        self.output.append(separator)
        try:
            with self.history_path.open("a", encoding="utf-8") as history:
                history.write(separator + "\n")
        except OSError:
            pass
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.instructions.setText(self.step_instruction_text(script_name))
        self.append(f"{self.tr('running_step')} {self.step_title(script_name)}")
        self.status.setText(self.tr("running"))
        self.current_script = script_name
        self.progress_start = time.monotonic()
        self.phase_start = self.progress_start
        self.step3_estimated_stage = ""
        self.last_progress_size = -1
        active_log = self.active_log_path(script_name)
        self.last_log_size = active_log.stat().st_size if active_log and active_log.exists() else 0
        self.progress.setText("")
        self.progress_timer.start()

        self.worker = StepWorker(command, env)
        self.worker.line.connect(self.append)
        self.worker.finished_code.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, code: int) -> None:
        self.progress_timer.stop()
        self.progress_bar.setRange(0, 100)
        finished_script = self.current_script
        if self.current_script in ("2_backup_flash.cmd", "3_backup_internal_flash.cmd"):
            self.poll_progress(force=True)
        self.append(f"Exit code: {code}")
        self.persist_active_log(finished_script)
        sync_from_runtime()
        if code == 0:
            self.progress_bar.setValue(100)
            state = self.current_state()
            if (
                finished_script == "3_backup_internal_flash.cmd"
                and state["payload_pending"]
                and not state["internal_backup"]
            ):
                self.show_step3_continue()
            else:
                self.instructions.setText(self.success_text(finished_script))
        else:
            self.instructions.setText(self.failure_text(finished_script))
            for line in self.explain_failure(finished_script):
                self.output.append(line)
        self.status.setText(self.tr("idle"))
        self.current_script = ""
        self.refresh_state()
        if code == 0 and finished_script == "4_unlock_device.cmd":
            self.instructions.setText(self.tr("auto_read_after_unlock"))
            QTimer.singleShot(800, lambda: self.start_step("1_sanity_check.cmd", False))
    def poll_progress(self, force: bool = False) -> None:
        if self.current_script == "3_backup_internal_flash.cmd":
            self.poll_step_log()
            return

        if self.current_script != "2_backup_flash.cmd":
            return

        backup_name = f"flash_backup_{self.target.currentText()}.bin"
        backup_path = RUNTIME_ROOT / "backups" / backup_name
        expected_size = 67_108_864

        if backup_path.exists():
            size = backup_path.stat().st_size
            label = backup_name
        else:
            size = 0
            label = self.tr("waiting_data")

        if size > 0:
            elapsed = max(time.monotonic() - self.progress_start, 0.001)
            percent = min(size * 100.0 / expected_size, 100.0)
            speed = size / elapsed / (1024 * 1024)
            text = (
                f"{self.tr('spi_read')}: {label}, "
                f"{size / (1024 * 1024):.1f}/{expected_size / (1024 * 1024):.1f} MB "
                f"({percent:.1f}%), {speed:.2f} MB/s"
            )
            self.progress_bar.setValue(int(max(0, min(percent, 100))))
            self.progress.setText(text)
            self.last_progress_size = size

    def active_log_path(self, script_name: str) -> Path | None:
        if script_name == "2_backup_flash.cmd":
            return LOGS / "2_openocd.log"
        if script_name == "3_backup_internal_flash.cmd":
            return LOGS / "3_openocd.log"
        if script_name == "4_unlock_device.cmd":
            return LOGS / "4_openocd.log"
        if script_name == "5_restore.cmd":
            return LOGS / "5_openocd.log"
        return None

    def persist_active_log(self, script_name: str) -> None:
        path = self.active_log_path(script_name)
        if not path or not path.exists():
            return
        try:
            detail = path.read_text(encoding="utf-8", errors="replace")
            with self.history_path.open("a", encoding="utf-8") as history:
                history.write(f"\n----- {path.name} -----\n")
                history.write(detail)
                if detail and not detail.endswith("\n"):
                    history.write("\n")
        except OSError:
            pass

    def step_title(self, script_name: str) -> str:
        return {
            "1_sanity_check.cmd": self.tr("step_1"),
            "2_backup_flash.cmd": self.tr("step_2"),
            "3_backup_internal_flash.cmd": self.tr("step_3"),
            "4_unlock_device.cmd": self.tr("step_4"),
            "5_restore.cmd": self.tr("step_5"),
        }.get(script_name, script_name)

    def step_instruction_text(self, script_name: str) -> str:
        if script_name == "1_sanity_check.cmd":
            return self.tr("instr_1")
        if script_name == "2_backup_flash.cmd":
            return self.tr("instr_2")
        if script_name == "3_backup_internal_flash.cmd":
            if self.marker_path(f"payload_pending_{self.current_target()}.ok").exists():
                return self.tr("instr_3_phase2")
            return self.tr("instr_3_phase1")
        if script_name == "4_unlock_device.cmd":
            return self.tr("instr_4")
        if script_name == "5_restore.cmd":
            return self.tr("instr_5")
        return ""

    def success_text(self, script_name: str) -> str:
        backup_steps = {
            "2_backup_flash.cmd",
            "3_backup_internal_flash.cmd",
            "4_unlock_device.cmd",
            "5_restore.cmd",
        }
        suffix = f"\n{self.tr('backup_warning')}" if script_name in backup_steps else ""
        if script_name == "4_unlock_device.cmd":
            return self.tr("success_4") + suffix
        if script_name == "5_restore.cmd":
            return self.tr("success_5") + suffix
        if script_name == "3_backup_internal_flash.cmd" and self.marker_path(
            f"payload_pending_{self.current_target()}.ok"
        ).exists():
            return self.tr("success_3_payload") + suffix
        return self.tr("success_generic") + suffix

    def failure_text(self, script_name: str) -> str:
        if script_name == "3_backup_internal_flash.cmd":
            return self.tr("fail_3")
        if script_name == "5_restore.cmd":
            return self.tr("fail_5")
        return self.tr("fail_generic")

    def full_log_hint(self, script_name: str) -> str:
        path = self.active_log_path(script_name)
        if path:
            return str(path)
        return str(self.history_path)

    def explain_failure(self, script_name: str) -> list[str]:
        text = "\n".join(self.step_raw_lines)
        model = self.current_target().capitalize()
        log_path = self.active_log_path(script_name)
        if log_path and log_path.exists():
            try:
                text += "\n" + log_path.read_text(encoding="utf-8", errors="replace")[-30000:]
            except OSError:
                pass

        if script_name == "2_backup_flash.cmd":
            if "another application is using the programmer" in text or "open failed" in text:
                if self.lang == "en":
                    return [
                        "Cause: ST-Link is busy in another application.",
                        "Close STM32CubeProgrammer, OpenOCD, and other debuggers, then repeat Step 2.",
                    ]
                return [
                    "Причина: ST-Link занят другой программой.",
                    "1. Закрой программы, использующие программатор.",
                    "2. Закрой STM32CubeProgrammer, OpenOCD и другие отладчики.",
                    "3. Не отключая питание устройства, повтори шаг 2.",
                ] if self.lang == "ru" else [
                    "Причина: ST-Link зайнятий іншою програмою.",
                    "1. Закрий програми, що використовують програматор.",
                    "2. Закрий STM32CubeProgrammer, OpenOCD та інші відлагоджувачі.",
                    "3. Не вимикаючи живлення пристрою, повтори крок 2.",
                ]
            if "unable to connect to the target" in text:
                if self.lang == "en":
                    return [
                        "Cause: ST-Link is detected but cannot connect to the MCU.",
                        "Check 1.8 V power, SWDIO, SWCLK, and GND, then repeat Step 2.",
                    ]
                return [
                    "Причина: ST-Link виден, но не подключается к процессору.",
                    "Проверь питание 1.8V, SWDIO, SWCLK, GND и повтори шаг 2.",
                ] if self.lang == "ru" else [
                    "Причина: ST-Link видно, але він не підключається до процесора.",
                    "Перевір живлення 1.8V, SWDIO, SWCLK, GND і повтори крок 2.",
                ]
            if "does not match the selected model" in text or "checksum is invalid" in text:
                if self.lang == "en":
                    return [
                        f"Cause: the device did not load the stock {model} code into ITCM.",
                        "The MCU firmware is missing, damaged, or the processor is in HardFault.",
                    ]
                return [
                    f"Причина: устройство не загрузило штатный код {model} в ITCM.",
                    f"Выбрана модель {model}, но считанные данные ей не соответствуют.",
                    "Внутренняя прошивка MCU отсутствует, повреждена или процессор находится в HardFault.",
                ] if self.lang == "ru" else [
                    f"Причина: пристрій не завантажив штатний код {model} в ITCM.",
                    f"Вибрано модель {model}, але прочитані дані їй не відповідають.",
                    "Внутрішня прошивка MCU відсутня, пошкоджена або процесор знаходиться у HardFault.",
                ]

        if script_name == "3_backup_internal_flash.cmd":
            if "communication failure" in text or "error waiting for target flash write algorithm" in text:
                if self.lang == "en":
                    return [
                        "Cause: communication with ST-Link was lost while programming SPI.",
                        "Power-cycle the device, press Power once without holding it, select 4000 or 2000 kHz, and repeat Step 3.",
                    ]
                return [
                    "Причина: во время записи SPI потеряна связь со ST-Link.",
                    "Передёрни питание, один раз нажми Power без удержания, выбери 4000 или 2000 кГц и повтори шаг 3.",
                ] if self.lang == "ru" else [
                    "Причина: під час запису SPI втрачено зв'язок зі ST-Link.",
                    "Передьорни живлення, один раз натисни Power без утримання, вибери 4000 або 2000 кГц і повтори крок 3.",
                ]
            if "Valid ITCM backup is missing" in text:
                if self.lang == "en":
                    return [
                        f"Cause: the stock {model} ITCM required to prepare the payload is missing.",
                        "The SPI backup can be created, but Step 3 requires a valid ITCM dump.",
                    ]
                return [
                    f"Причина: нет штатного ITCM {model}, необходимого для подготовки payload.",
                    "Внутренняя прошивка MCU сейчас не запускается или повреждена.",
                    "SPI backup можно сделать, но Step 3 без правильного ITCM продолжить нельзя.",
                ] if self.lang == "ru" else [
                    f"Причина: немає штатного ITCM {model}, потрібного для підготовки payload.",
                    "Внутрішня прошивка MCU зараз не запускається або пошкоджена.",
                    "SPI backup можна зробити, але Step 3 без правильного ITCM продовжити неможливо.",
                ]
            if "Handler HardFault" in text or "pc: 0xfffffffe" in text:
                if self.lang == "en":
                    return [
                        "Cause: the payload is not running; the processor is in HardFault.",
                        "Power-cycle the device, hold Power, wait for the blue screen, and repeat Step 3 while holding Power.",
                    ]
                return [
                    "Причина: payload не запущен, процессор находится в HardFault.",
                    "1. Отключи питание устройства.",
                    "2. Подай питание снова.",
                    "3. Зажми Power и не отпускай.",
                    "4. Дождись синего экрана. Если его нет, один раз нажми Time.",
                    "5. Не отпуская Power, снова запусти шаг 3.",
                ] if self.lang == "ru" else [
                    "Причина: payload не запущено, процесор знаходиться у HardFault.",
                    "1. Вимкни живлення пристрою.",
                    "2. Подай живлення знову.",
                    "3. Затисни Power і не відпускай.",
                    "4. Дочекайся синього екрана. Якщо його немає, один раз натисни Time.",
                    "5. Не відпускаючи Power, знову запусти крок 3.",
                ]
            if "Invalid STM32 vector table" in text or "not a valid STM32 firmware image" in text:
                if self.lang == "en":
                    return [
                        "Cause: the data read is not valid MCU firmware.",
                        "Repeat the blue-screen procedure and Step 3.",
                    ]
                return [
                    "Причина: считан неправильный участок памяти, это не MCU firmware.",
                    "Повтори процедуру синего экрана и шаг 3.",
                ] if self.lang == "ru" else [
                    "Причина: прочитано неправильну ділянку пам'яті, це не MCU firmware.",
                    "Повтори процедуру синього екрана і крок 3.",
                ]
            if "unable to connect to the target" in text:
                if self.lang == "en":
                    return [
                        "Cause: ST-Link could not connect to the MCU.",
                        "Check power and SWD wiring, then repeat the step.",
                    ]
                return [
                    "Причина: ST-Link не подключился к процессору.",
                    "Проверь питание, SWD-провода и повтори шаг.",
                ] if self.lang == "ru" else [
                    "Причина: ST-Link не підключився до процесора.",
                    "Перевір живлення, SWD-дроти та повтори крок.",
                ]

        if script_name == "5_restore.cmd":
            if "DP error" in text or "STLink error" in text or "GNW_ERROR" in text:
                if self.lang == "en":
                    return [
                        "Cause: ST-Link lost the debug connection during SPI restore.",
                        "Power-cycle the device, wait two seconds, select 4000 or 2000 kHz, and repeat Step 5.",
                    ]
                return [
                    "Причина: во время восстановления SPI потеряна связь со ST-Link.",
                    "Передёрни питание устройства, подожди 2 секунды, выбери 4000 или 2000 кГц и повтори шаг 5.",
                ] if self.lang == "ru" else [
                    "Причина: під час відновлення SPI втрачено зв'язок зі ST-Link.",
                    "Передьорни живлення пристрою, зачекай 2 секунди, вибери 4000 або 2000 кГц і повтори крок 5.",
                ]
            if "Target not halted" in text or "timed out while waiting for target halted" in text:
                if self.lang == "en":
                    return [
                        "Cause: the MCU started before the separate readback connection could halt it.",
                        "The updated restore keeps programming and readback in one OpenOCD session. Repeat Step 5.",
                    ]
                return [
                    "Причина: MCU запустился до повторного подключения для проверки.",
                    "Теперь запись и контрольное чтение выполняются за один сеанс OpenOCD. Повтори шаг 5.",
                ] if self.lang == "ru" else [
                    "Причина: MCU запустився до повторного підключення для перевірки.",
                    "Тепер запис і контрольне читання виконуються за один сеанс OpenOCD. Повтори крок 5.",
                ]

        error_lines = [
            line.strip()
            for line in text.splitlines()
            if any(token in line.lower() for token in ("error:", "failed", "mismatch", "invalid", "unable"))
        ]
        if error_lines:
            return error_lines[-6:]
        return [self.failure_text(script_name)]

    def marker_path(self, name: str) -> Path:
        return STATE / name

    def backup_path(self, name: str) -> Path:
        return BACKUPS / name

    def current_target(self) -> str:
        return self.target.currentText()

    def current_state(self) -> dict[str, bool]:
        target = self.current_target()
        spi_path = self.backup_path(f"flash_backup_{target}.bin")
        internal_path = self.backup_path(f"internal_flash_backup_{target}.bin")
        internal_custom_sha1 = self.backup_path(f"internal_flash_backup_{target}.bin.actual.sha1")
        stable_internal = (
            internal_path.exists()
            and internal_path.stat().st_size == 131072
            and internal_custom_sha1.exists()
            and self.marker_path(f"internal_backup_{target}.ok").exists()
        )
        protection_unlocked = self.marker_path(f"protection_unlocked_{target}.ok").exists()
        internal_backup = self.verify_sha1_file(
            RUNTIME_ROOT / "shasums" / f"internal_flash_backup_{target}.bin.sha1"
        ) or stable_internal
        return {
            "sanity": self.marker_path(f"sanity_{target}.ok").exists(),
            "spi_backup": spi_path.exists() and spi_path.stat().st_size == 67_108_864,
            "payload_pending": (
                self.marker_path(f"payload_pending_{target}.ok").exists()
                and not internal_backup
            ),
            "internal_backup": internal_backup,
            "protection_unlocked": protection_unlocked,
            "unlock": self.marker_path(f"unlock_{target}.ok").exists(),
            "restore": self.marker_path(f"restore_{target}.ok").exists(),
            "internal_exists": internal_path.exists(),
        }

    def verify_sha1_file(self, sha1_path: Path) -> bool:
        try:
            line = sha1_path.read_text(encoding="utf-8").strip().splitlines()[0]
            parts = line.split()
            if len(parts) < 2:
                return False
            expected = parts[0].lower()
            payload_path = RUNTIME_ROOT / parts[1].replace("/", os.sep)
            if payload_path.parts and "backups" in payload_path.parts:
                payload_path = BACKUPS / payload_path.name
            if not payload_path.exists():
                return False
            digest = hashlib.sha1()
            with payload_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest().lower() == expected
        except OSError:
            return False

    def is_step_complete(self, script_name: str, state: dict[str, bool]) -> bool:
        return {
            "1_sanity_check.cmd": state["sanity"],
            "2_backup_flash.cmd": state["spi_backup"],
            "3_backup_internal_flash.cmd": state["internal_backup"],
            "4_unlock_device.cmd": state["unlock"],
            "5_restore.cmd": state["restore"],
        }.get(script_name, False)

    def can_run_step(self, script_name: str, state: dict[str, bool]) -> bool:
        if script_name == "1_sanity_check.cmd":
            return True
        if state["protection_unlocked"]:
            return script_name == "5_restore.cmd" and state["spi_backup"] and state["internal_backup"]
        if script_name == "4_unlock_device.cmd":
            return state["spi_backup"] and state["internal_backup"]
        if script_name == "5_restore.cmd":
            return False
        return True

    def disabled_reason(self, script_name: str, state: dict[str, bool]) -> str:
        if state["protection_unlocked"]:
            return self.tr("disabled_unlocked")
        if script_name == "4_unlock_device.cmd":
            return self.tr("need_internal_backup")
        return self.tr("disabled_generic")

    def completed_message(self, script_name: str) -> str:
        messages = {
            "1_sanity_check.cmd": self.tr("already_1"),
            "2_backup_flash.cmd": self.tr("already_2"),
            "3_backup_internal_flash.cmd": self.tr("already_3"),
            "4_unlock_device.cmd": self.tr("already_4"),
            "5_restore.cmd": self.tr("already_5"),
        }
        return messages.get(script_name, self.tr("already_done_title"))

    def refresh_state(self) -> None:
        state = self.current_state()
        self.update_model_style()
        for script_name, button in self.buttons.items():
            button.setText(self.step_title(script_name))
            button.setEnabled(self.can_run_step(script_name, state))
            if self.is_step_complete(script_name, state):
                button.setStyleSheet("QPushButton { background-color: #167a35; color: white; font-weight: bold; }")
            elif script_name == "3_backup_internal_flash.cmd" and state["payload_pending"]:
                button.setStyleSheet("QPushButton { background-color: #b7791f; color: white; font-weight: bold; }")
            else:
                button.setStyleSheet("")

        parts = []
        if self.protection_status == "unlocked":
            parts.append(self.format_status_part(self.tr("protection_unlocked"), "#19a34a"))
        elif self.protection_status == "locked":
            parts.append(self.format_status_part(self.tr("protection_locked"), "#e32929"))
        else:
            parts.append(self.tr("protection_unknown"))
        parts.append(self.tr("spi_ok") if state["spi_backup"] else self.tr("spi_missing"))
        if state["internal_backup"]:
            parts.append(self.tr("internal_ok"))
        elif state["payload_pending"]:
            parts.append(self.tr("internal_wait"))
        elif state["internal_exists"]:
            parts.append(self.tr("internal_invalid"))
        else:
            parts.append(self.tr("internal_missing"))
        parts.append(self.tr("unlock_done") if state["unlock"] else self.tr("unlock_not_done"))
        parts.append(self.tr("restore_done") if state["restore"] else self.tr("restore_not_done"))
        self.state_label.setText(" | ".join(parts))
        self.step3_continue.setVisible(state["payload_pending"] and not state["internal_backup"])
        if self.protection_status == "unlocked" and not self.current_script:
            message_key = (
                "already_unlocked_with_backup"
                if state["spi_backup"] and state["internal_backup"]
                else "already_unlocked_no_backup"
            )
            self.instructions.setText(self.tr(message_key))
        elif state["payload_pending"] and not state["internal_backup"] and not self.current_script:
            self.instructions.setText(self.tr("step3_continue"))

    def format_status_part(self, text: str, color: str) -> str:
        if ":" not in text:
            return f"<span style='color:{color}; font-weight:700;'>{text}</span>"
        prefix, _, value = text.partition(":")
        return f"{prefix}: <span style='color:{color}; font-weight:800;'>{value.strip()}</span>"

    def update_model_style(self) -> None:
        if self.target.currentText() == "zelda":
            self.target.setStyleSheet("QComboBox { background-color: #126b38; color: white; font-weight: bold; }")
        else:
            self.target.setStyleSheet("QComboBox { background-color: #b91c1c; color: white; font-weight: bold; }")

    def poll_step_log(self) -> None:
        log_path = self.active_log_path(self.current_script)
        if not log_path or not log_path.exists():
            elapsed = int(time.monotonic() - self.progress_start)
            self.progress.setText(f"{self.tr('step_active')}: {elapsed}s")
            return
        current_size = log_path.stat().st_size
        elapsed = int(time.monotonic() - self.progress_start)
        if self.step3_estimated_stage == "payload_write":
            phase_elapsed = max(time.monotonic() - self.phase_start, 0.0)
            self.progress.setText(
                f"{self.tr('payload_write')}: {int(phase_elapsed)}s, {self.tr('log')} {current_size / 1024:.0f} KB"
            )
        else:
            self.progress.setText(f"{self.tr('step_active')}: {elapsed}s, {self.tr('log')} {current_size / 1024:.0f} KB")
        if current_size > self.last_log_size:
            with log_path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(self.last_log_size)
                chunk = handle.read()
            self.last_log_size = current_size
            for line in chunk.splitlines()[-8:]:
                if line.strip():
                    self.append("[openocd] " + line.rstrip())



def main() -> int:
    if "--internal-python" in sys.argv:
        index = sys.argv.index("--internal-python")
        return internal_python_main(sys.argv[index + 1:])
    LOGS.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    if APP_ICON.exists():
        app.setWindowIcon(QIcon(str(APP_ICON)))
    window = MainWindow()
    if "--smoke-test" in sys.argv:
        required = (
            STEPS / "1_sanity_check.cmd",
            ASSET_ROOT / "tools" / "protection_check.py",
            ASSET_ROOT / "vendor" / "openocd" / "bin" / "openocd.exe",
            RUNTIME_ROOT / "openocd" / "rdp0.cfg",
        )
        return 0 if all(path.exists() for path in required) else 2
    show_about_dialog(window, current_program_sha256())
    window.show()
    return app.exec()


def show_about_dialog(parent: QWidget, sha256: str) -> None:
    message = QMessageBox(parent)
    message.setWindowTitle("About")
    if APP_ICON.exists():
        message.setWindowIcon(QIcon(str(APP_ICON)))
    if APP_LOGO.exists():
        pixmap = QPixmap(str(APP_LOGO))
        if not pixmap.isNull():
            message.setIconPixmap(pixmap.scaledToWidth(96))
    message.setText("GWUnlock")
    message.setInformativeText(
        f"Version: {APP_VERSION}\n"
        f"Build Date: {BUILD_DATE}\n"
        f"SHA256:\n{sha256}"
    )
    message.setStandardButtons(QMessageBox.StandardButton.Ok)
    message.exec()


if __name__ == "__main__":
    raise SystemExit(main())
