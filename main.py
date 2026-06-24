import sys
import re
import time
from datetime import datetime
from collections import Counter, defaultdict
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QTextEdit, QPushButton, QLabel, QFileDialog,
                             QHeaderView, QFrame, QSplitter, QComboBox, QLineEdit, 
                             QProgressBar, QMessageBox, QStatusBar)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont

STYLE = """
QMainWindow { background-color: #0a0e14; }
QWidget { background-color: #0a0e14; color: #c9d1d9; font-family: 'Segoe UI', 'Consolas', monospace; font-size: 13px; }
QFrame#TopBar { background-color: #111820; border-bottom: 2px solid #2a3340; }
QFrame#Card { background-color: #111820; border: 1px solid #2a3340; border-radius: 10px; padding: 15px; }
QPushButton { background-color: #1a2330; border: 1px solid #2a3340; border-radius: 8px; padding: 10px 20px; color: #58a6ff; font-weight: bold; font-size: 13px; }
QPushButton:hover { background-color: #1f2d3d; border-color: #58a6ff; }
QPushButton#PrimaryBtn { background-color: #1a3a2a; border-color: #238636; color: #3fb950; }
QPushButton#PrimaryBtn:hover { background-color: #1f4a35; }
QPushButton#DangerBtn { background-color: #3a1a1a; border-color: #8b2a2a; color: #f85149; }
QPushButton#AccentBtn { background-color: #1c1a3a; border-color: #6e40c9; color: #a371f7; }
QComboBox { background-color: #1a2330; border: 1px solid #2a3340; border-radius: 6px; padding: 6px 12px; color: #c9d1d9; }
QComboBox:hover { border-color: #58a6ff; }
QComboBox QAbstractItemView { background-color: #111820; border: 1px solid #2a3340; }
QLineEdit { background-color: #0d1117; border: 2px solid #2a3340; border-radius: 8px; padding: 10px 16px; color: #f0f6fc; font-size: 14px; }
QLineEdit:focus { border-color: #58a6ff; }
QTextEdit { background-color: #0d1117; border: 2px solid #2a3340; border-radius: 10px; padding: 12px; color: #e6edf3; line-height: 1.6; }
QTableWidget { background-color: #0d1117; border: 1px solid #2a3340; gridline-color: #1a2330; border-radius: 8px; }
QTableWidget::item:selected { background-color: rgba(31, 111, 235, 0.3); }
QHeaderView::section { background-color: #111820; color: #8b949e; padding: 10px; border: 1px solid #2a3340; font-weight: bold; text-transform: uppercase; font-size: 11px; }
QProgressBar { border: 2px solid #2a3340; border-radius: 8px; background-color: #0d1117; color: white; font-weight: bold; height: 20px; }
QProgressBar::chunk { background-color: #238636; border-radius: 6px; }
QSplitter::handle { background-color: #2a3340; width: 2px; }
QStatusBar { background-color: #111820; border-top: 1px solid #2a3340; }
"""

LOG_PATTERNS = [
    re.compile(r'\[(?P<time>\d{2}:\d{2}:\d{2})\]\s+\[(?P<thread>[^\]]+)\]\s*\[(?P<level>INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\]:\s*(?P<msg>.*)', re.I),
    re.compile(r'(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+\[(?P<level>ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL|FATAL|TRACE|FAIL)\]\s*(?:\[(?P<thread>[^\]]+)\]\s*)?(?P<msg>.*)', re.I),
    re.compile(r'(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+\[(?P<level>ERROR|WARN|INFO|CRITICAL|FAIL|PANIC|FATAL|SECURITY)\]\s+(?P<msg>.*)', re.I),
]

LEVEL_MAP = {
    'critical': 'CRITICAL', 'crit': 'CRITICAL', 'fatal': 'CRITICAL', 'emerg': 'CRITICAL',
    'error': 'ERROR', 'err': 'ERROR', 'fail': 'ERROR', 'panic': 'ERROR',
    'warn': 'WARNING', 'warning': 'WARNING',
    'info': 'INFO', 'notice': 'NOTICE', 'debug': 'DEBUG', 'trace': 'DEBUG'
}


class SmartAI:
    @staticmethod
    def count_in_text(text, keywords):
        if not text: return 0
        return sum(1 for kw in keywords if kw in text)

    @staticmethod
    def analyze_line(line_text, full_log, lang="RU"):
        if not line_text: return ""
        line = line_text.lower()
        log = full_log.lower() if full_log else ""
        ru = lang == "RU"

        # ШЕЙДЕРЫ
        if any(kw in line for kw in ["shader", "opengl", "glsl", "vertex shader", "fragment shader", "compile", "glLinkProgram", "glCompileShader"]):
            similar = SmartAI.count_in_text(log, ["shader", "compile", "link", "program error"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🎨 ОШИБКИ ШЕЙДЕРОВ / OpenGL</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">ШЕЙДЕРЫ НЕ КОМПИЛИРУЮТСЯ</span></div>
<div style="background: rgba(88,166,255,0.1); border-left: 4px solid #58a6ff; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #58a6ff;">📋 ЧТО СЛУЧИЛОСЬ:</b> Шейдеры используют старый GLSL (#version 110), не поддерживаемый OpenGL 3+ forward-compatible контекстом.</div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ КАК ИСПРАВИТЬ:</b><br>1. Добавьте <b>#version 330 core</b> в начало шейдеров<br>2. Замените: gl_FragColor→out vec4 FragColor; attribute→in; varying→out/in; texture2D→texture<br>3. Или используйте совместимый контекст OpenGL</div>
<p style="color: #8b949e;">📊 Похожих ошибок: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🎨 SHADER / OpenGL ERRORS</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">SHADERS FAIL TO COMPILE</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. Add #version 330 core<br>2. Replace deprecated GLSL functions<br>3. Or use compatibility context</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # DNS
        if any(kw in line for kw in ["unknown host", "неизвестный сервер", "cannot resolve", "name resolution", "nxdomain"]):
            host = re.search(r'(?:ping|cannot resolve|unknown host)[:\s]+([^\s:]+)', line_text, re.I)
            host = host.group(1) if host else "указанный хост"
            similar = SmartAI.count_in_text(log, ["unknown host", "неизвестный сервер", "cannot resolve"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🌐 DNS-ОШИБКА</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">DNS НЕ РАЗРЕШАЕТ ИМЯ {host}</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. nslookup {host}<br>2. Смените DNS на 8.8.8.8<br>3. Проверьте /etc/hosts<br>4. Попробуйте по IP</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🌐 DNS ERROR</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">DNS CANNOT RESOLVE {host}</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. nslookup {host}<br>2. Use DNS 8.8.8.8<br>3. Check /etc/hosts</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Connection Refused
        if any(kw in line for kw in ["connection refused", "connection reset", "econnrefused", "econnreset"]):
            similar = SmartAI.count_in_text(log, ["connection refused", "connection reset"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🚫 ОТКАЗ В ПОДКЛЮЧЕНИИ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">СЕРВЕР ОТКЛОНЯЕТ ПОДКЛЮЧЕНИЕ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. systemctl status [сервис]<br>2. netstat -tlnp | grep [порт]<br>3. Проверьте файрвол<br>4. Слушать на 0.0.0.0</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🚫 CONNECTION REFUSED</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">SERVER REFUSING</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. systemctl status<br>2. netstat -tlnp<br>3. Check firewall</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Timeout
        if any(kw in line for kw in ["timeout", "timed out"]):
            similar = SmartAI.count_in_text(log, ["timeout", "timed out"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">⏱️ ТАЙМАУТ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">СЕРВЕР НЕ ОТВЕТИЛ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. ping сервер<br>2. Проверьте загрузку<br>3. Увеличьте таймаут<br>4. Проверьте сеть</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">⏱️ TIMEOUT</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">NO RESPONSE</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. ping<br>2. Check load<br>3. Increase timeout</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Memory
        if any(kw in line for kw in ["out of memory", "oom", "heap space", "memory leak", "killed process"]):
            similar = SmartAI.count_in_text(log, ["out of memory", "oom", "heap space", "killed process"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">💾 НЕХВАТКА ПАМЯТИ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">СИСТЕМА ИСЧЕРПАЛА RAM</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. Увеличьте -Xmx<br>2. Добавьте swap<br>3. jmap -dump<br>4. Закройте программы</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">💾 MEMORY</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">OUT OF RAM</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. Increase -Xmx<br>2. Add swap<br>3. jmap</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Permission
        if any(kw in line for kw in ["permission denied", "access denied", "eacces"]):
            similar = SmartAI.count_in_text(log, ["permission denied", "access denied", "eacces"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🔐 НЕДОСТАТОЧНО ПРАВ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">ОТКАЗАНО В ДОСТУПЕ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. ls -la [путь]<br>2. chown user:group<br>3. chmod 755<br>4. Проверьте SELinux</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🔐 PERMISSION DENIED</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">ACCESS DENIED</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. ls -la<br>2. chown<br>3. chmod</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Database
        if any(kw in line for kw in ["database", "sql", "mysql", "postgres", "deadlock", "duplicate entry"]):
            similar = SmartAI.count_in_text(log, ["database", "sql", "mysql", "postgres", "deadlock"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🗄️ ОШИБКА БД</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">СБОЙ БАЗЫ ДАННЫХ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. systemctl status БД<br>2. Проверьте логи<br>3. max_connections<br>4. Проверьте права</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🗄️ DB ERROR</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">DB FAILURE</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. Check status<br>2. Check logs<br>3. max_connections</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Crash
        if any(kw in line for kw in ["segfault", "core dump", "null pointer", "signal 11"]):
            similar = SmartAI.count_in_text(log, ["segfault", "core dump", "null pointer"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">💥 АВАРИЙНЫЙ КРАШ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">ПРИЛОЖЕНИЕ УПАЛО</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. gdb core<br>2. memtest86+<br>3. Обновите ПО<br>4. Проверьте библиотеки</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">💥 CRASH</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">APP CRASHED</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. gdb core<br>2. memtest86+<br>3. Update</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # File Not Found
        if any(kw in line for kw in ["file not found", "no such file", "enoent"]):
            similar = SmartAI.count_in_text(log, ["file not found", "no such file"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">📁 ФАЙЛ НЕ НАЙДЕН</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">ФАЙЛ ОТСУТСТВУЕТ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. ls -la [путь]<br>2. Проверьте путь<br>3. Переустановите пакет</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">📁 FILE NOT FOUND</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">FILE MISSING</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. ls -la<br>2. Verify path<br>3. Reinstall</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Security
        if any(kw in line for kw in ["failed password", "brute force", "invalid user"]):
            similar = SmartAI.count_in_text(log, ["failed password", "brute force"])
            if ru:
                return f"""<h3 style="color: #8b5cf6;">🔒 БЕЗОПАСНОСТЬ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">НЕУДАЧНЫЙ ВХОД</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ РЕШЕНИЕ:</b><br>1. fail2ban<br>2. Смените пароли<br>3. SSH-ключи</div>
<p style="color: #8b949e;">📊 Похожих: <b>{similar}</b></p>"""
            else:
                return f"""<h3 style="color: #8b5cf6;">🔒 SECURITY</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">FAILED LOGIN</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. fail2ban<br>2. Change passwords</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # Program Error (контекстный)
        if any(kw in line for kw in ["program error", "link failed", "compilation error"]):
            context_has_shader = "shader" in log or "opengl" in log or "vertex" in log or "fragment" in log
            if context_has_shader:
                similar = SmartAI.count_in_text(log, ["shader", "compile", "link", "program error"])
                if ru:
                    return f"""<h3 style="color: #8b5cf6;">🎨 ОШИБКА ШЕЙДЕРНОЙ ПРОГРАММЫ</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 ДИАГНОЗ:</b> <span style="font-size: 16px;">ШЕЙДЕРЫ НЕ СКОМПИЛИРОВАНЫ</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ КАК ИСПРАВИТЬ:</b><br>1. Добавьте #version 330 core в шейдеры<br>2. Исправьте ошибки компиляции (см. строки выше)<br>3. После компиляции вызывайте glLinkProgram</div>
<p style="color: #8b949e;">📊 Ошибок шейдеров: <b>{similar}</b></p>"""
                else:
                    return f"""<h3 style="color: #8b5cf6;">🎨 SHADER PROGRAM ERROR</h3>
<div style="background: rgba(248,81,73,0.15); border-left: 4px solid #f85149; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #f85149;">🚨 DIAGNOSIS:</b> <span style="font-size: 16px;">SHADERS NOT COMPILED</span></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">🛠️ FIX:</b><br>1. Add #version 330 core<br>2. Fix compilation errors<br>3. Then call glLinkProgram</div>
<p style="color: #8b949e;">📊 Similar: <b>{similar}</b></p>"""

        # FALLBACK
        errors_total = SmartAI.count_in_text(log, ["error", "fail", "critical", "fatal", "exception"])
        words = re.findall(r'\b[a-zA-Zа-яА-Я0-9._/-]{4,}\b', line_text.lower())
        stop = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'then', 'than', 'app', 'system', 'main', 'render', 'thread', 'info', 'warn', 'error', 'program'}
        keywords = [w for w in words if w not in stop][:6]
        if ru:
            return f"""<h3 style="color: #ffd93d;">⚠️ ОШИБКА</h3>
<div style="background: rgba(139,92,246,0.1); padding: 10px; border-radius: 6px;"><code>{line_text[:300]}</code></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">💡 РЕКОМЕНДАЦИИ:</b><br>1. Проверьте логи до и после<br>2. Перезапустите сервис<br>3. Проверьте конфигурацию</div>
<p style="color: #8b949e;">📊 Всего ошибок: <b>{errors_total}</b> | Слова: {', '.join(keywords) if keywords else 'нет'}</p>"""
        else:
            return f"""<h3 style="color: #ffd93d;">⚠️ ERROR</h3>
<div style="background: rgba(139,92,246,0.1); padding: 10px; border-radius: 6px;"><code>{line_text[:300]}</code></div>
<div style="background: rgba(63,185,80,0.1); border-left: 4px solid #3fb950; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #3fb950;">💡 RECOMMENDATIONS:</b><br>1. Check logs<br>2. Restart service<br>3. Check config</div>
<p style="color: #8b949e;">📊 Total errors: <b>{errors_total}</b> | Keywords: {', '.join(keywords) if keywords else 'none'}</p>"""

    @staticmethod
    def global_analysis(full_log, data, lang="RU"):
        if not full_log: return ""
        log = full_log.lower()
        ru = lang == "RU"

        cats = [
            ("🎨 ШЕЙДЕРЫ", ["shader", "opengl", "compile", "link", "program error"]),
            ("🌐 DNS", ["unknown host", "неизвестный сервер", "cannot resolve"]),
            ("🚫 ОТКАЗЫ", ["connection refused", "connection reset"]),
            ("⏱️ ТАЙМАУТЫ", ["timeout", "timed out"]),
            ("💾 ПАМЯТЬ", ["out of memory", "oom", "heap space", "killed process"]),
            ("💿 ДИСК", ["no space", "disk full"]),
            ("🔐 ДОСТУП", ["permission denied", "access denied"]),
            ("🗄️ БД", ["database", "sql", "mysql", "postgres", "deadlock"]),
            ("🔒 БЕЗОПАСНОСТЬ", ["failed password", "brute force"]),
            ("💥 КРАШИ", ["segfault", "core dump", "null pointer"]),
            ("📁 ФАЙЛЫ", ["file not found", "no such file"]),
            ("⚡ СЛУЖБЫ", ["service fail", "process died", "exit code"]),
        ]
        if not ru:
            cats = [
                ("🎨 SHADERS", ["shader", "opengl", "compile", "link", "program error"]),
                ("🌐 DNS", ["unknown host", "cannot resolve"]),
                ("🚫 REFUSED", ["connection refused", "connection reset"]),
                ("⏱️ TIMEOUTS", ["timeout", "timed out"]),
                ("💾 MEMORY", ["out of memory", "oom", "heap space", "killed process"]),
                ("💿 DISK", ["no space", "disk full"]),
                ("🔐 ACCESS", ["permission denied", "access denied"]),
                ("🗄️ DB", ["database", "sql", "mysql", "postgres", "deadlock"]),
                ("🔒 SECURITY", ["failed password", "brute force"]),
                ("💥 CRASHES", ["segfault", "core dump", "null pointer"]),
                ("📁 FILES", ["file not found", "no such file"]),
                ("⚡ SERVICES", ["service fail", "process died", "exit code"]),
            ]

        results = [(name, SmartAI.count_in_text(log, keywords)) for name, keywords in cats if SmartAI.count_in_text(log, keywords) > 0]
        results.sort(key=lambda x: x[1], reverse=True)
        primary = results[0] if results else None

        html = f"<h2 style=\"color: #58a6ff;\">🧠 {'АНАЛИЗ ВСЕГО ЛОГА' if ru else 'FULL LOG ANALYSIS'}</h2>"
        html += f"""<div style="background: rgba(88,166,255,0.08); border-left: 4px solid #58a6ff; padding: 12px; margin: 10px 0; border-radius: 6px;">
<b style="color: #58a6ff;">📊 {'СТАТИСТИКА' if ru else 'STATISTICS'}:</b><br>
{'Всего строк' if ru else 'Total'}: <b>{data.get('total', 0)}</b> | 
{'Ошибок' if ru else 'Errors'}: <b style="color: #f85149;">{data.get('errors', 0)}</b> | 
{'Предупреждений' if ru else 'Warnings'}: <b style="color: #ffd93d;">{data.get('warns', 0)}</b></div>"""
        
        if primary:
            html += f"""<div style="background: rgba(248,81,73,0.12); border-left: 4px solid #f85149; padding: 14px; margin: 12px 0; border-radius: 6px;">
<b style="color: #f85149; font-size: 15px;">🚨 {'ГЛАВНАЯ ПРОБЛЕМА' if ru else 'MAIN ISSUE'}: {primary[0]}</b><br>
<span style="color: #8b949e;">{'Совпадений' if ru else 'Matches'}: <b>{primary[1]}</b></span></div>"""
        else:
            html += f"<p style=\"color: #3fb950;\">✅ {'Ошибок не найдено.' if ru else 'No errors found.'}</p>"
        
        if results:
            html += f"<br><b>{'📈 КАТЕГОРИИ' if ru else '📈 CATEGORIES'}:</b><br>"
            for name, count in results:
                html += f"• {name}: <b>{count}</b><br>"
        
        html += f"<p style=\"color: #8b949e; margin-top: 12px;\">💡 {'Выберите строку для детального анализа.' if ru else 'Select a line for detailed analysis.'}</p>"
        return html


class ParserWorker(QThread):
    row_ready = pyqtSignal(dict)
    done = pyqtSignal(dict)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def parse(self, line):
        line = line.strip()
        if not line: return None
        for p in LOG_PATTERNS:
            m = p.match(line)
            if m:
                g = m.groupdict()
                lvl = LEVEL_MAP.get(g.get('level', 'info').lower(), 'INFO').upper()
                return {'time': g.get('time', '--:--:--'), 'level': lvl, 'service': g.get('thread', 'System'), 'msg': g.get('msg', line), 'raw': line}
        ll = line.lower()
        lvl = 'INFO'
        for kw, l in [('critical', 'CRITICAL'), ('fatal', 'CRITICAL'), ('error', 'ERROR'), ('exception', 'ERROR'), ('fail', 'ERROR'), ('warn', 'WARNING')]:
            if kw in ll: lvl = l; break
        return {'time': '--:--:--', 'level': lvl, 'service': 'System', 'msg': line, 'raw': line}

    def run(self):
        errs = warns = 0
        svcs, raw = [], []
        tl = defaultdict(int)
        try:
            with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [l for l in f.readlines() if l.strip()]
            total = len(lines)
            if total == 0: self.error.emit("Empty file"); return
            for i, line in enumerate(lines):
                p = self.parse(line)
                if not p: continue
                svcs.append(p['service'])
                if p['level'] in ('CRITICAL', 'ERROR'): errs += 1
                elif p['level'] == 'WARNING': warns += 1
                raw.append(line.lower())
                h = p['time'][:2] if len(p['time']) >= 2 else '00'
                if h.isdigit(): tl[h] += 1
                self.row_ready.emit(p)
                if i % 200 == 0: self.progress.emit(int((i / total) * 100)); self.msleep(1)
            top = Counter(svcs).most_common(5)
            self.done.emit({'total': total, 'errors': errs, 'warns': warns, 'dump': ' '.join(raw), 'top': top, 'timeline': dict(sorted(tl.items()))})
            self.progress.emit(100)
        except FileNotFoundError: self.error.emit(f"File not found: {self.path}")
        except Exception as e: self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "RU"
        self.analysis = None
        self.full_log = ""
        self.selected_line = None
        self.setWindowTitle("⚡ AI-LogPulse v5.0 | by hero684k")
        self.resize(1550, 900)
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(STYLE)
        self.init_ui()
        self.connect_all()

    def t(self, key):
        pack = {
            "RU": {"open": "📂 ОТКРЫТЬ ЛОГ", "export": "💾 ЭКСПОРТ", "clear": "🗑️ ОЧИСТИТЬ",
                   "search": "🔍 Поиск...", "ready": "🟢 Готов", "parsing": "🔄 Анализ...", "done": "✅ Завершено",
                   "btn_global": "🤖 АНАЛИЗ ВСЕГО ЛОГА", "btn_line": "🤖 АНАЛИЗ СТРОКИ",
                   "timeline": "⏱️ АКТИВНОСТЬ", "welcome_global": "Загрузите лог-файл", "welcome_line": "Выберите строку"},
            "EN": {"open": "📂 OPEN LOG", "export": "💾 EXPORT", "clear": "🗑️ CLEAR",
                   "search": "🔍 Search...", "ready": "🟢 Ready", "parsing": "🔄 Analyzing...", "done": "✅ Done",
                   "btn_global": "🤖 ANALYZE ALL", "btn_line": "🤖 ANALYZE LINE",
                   "timeline": "⏱️ ACTIVITY", "welcome_global": "Load a log file", "welcome_line": "Select a line"}
        }
        return pack.get(self.lang, pack["RU"]).get(key, key)

    def init_ui(self):
        main = QVBoxLayout(); main.setContentsMargins(0, 0, 0, 0); main.setSpacing(0)
        
        top = QFrame(); top.setObjectName("TopBar"); top.setFixedHeight(75)
        tl = QHBoxLayout(top); tl.setContentsMargins(15, 8, 15, 8); tl.setSpacing(10)
        title_lbl = QLabel("⚡ AI-LogPulse v5.0 | by hero684k")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff; letter-spacing: 2px;")
        self.btn_open = QPushButton(self.t("open")); self.btn_open.setObjectName("PrimaryBtn")
        self.btn_export = QPushButton(self.t("export")); self.btn_export.setEnabled(False)
        self.btn_clear = QPushButton(self.t("clear")); self.btn_clear.setObjectName("DangerBtn")
        self.progress = QProgressBar(); self.progress.setFixedWidth(180); self.progress.setValue(0)
        self.status_lbl = QLabel(self.t("ready"))
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 12px; padding: 4px 10px; background: rgba(42,51,64,0.5); border-radius: 4px;")
        self.combo_lang = QComboBox(); self.combo_lang.addItems(["RU", "EN"]); self.combo_lang.setFixedWidth(70)
        tl.addWidget(title_lbl); tl.addSpacing(15); tl.addWidget(self.btn_open); tl.addWidget(self.btn_export)
        tl.addWidget(self.btn_clear); tl.addSpacing(10); tl.addWidget(self.progress); tl.addWidget(self.status_lbl)
        tl.addStretch(); tl.addWidget(self.combo_lang); main.addWidget(top)

        self.search = QLineEdit(); self.search.setPlaceholderText(self.t("search")); self.search.setFixedHeight(42)
        sf = QFrame(); sf.setStyleSheet("padding: 6px 15px;"); sl = QHBoxLayout(sf); sl.setContentsMargins(0,0,0,0); sl.addWidget(self.search)
        main.addWidget(sf)

        split = QSplitter(Qt.Orientation.Horizontal); split.setChildrenCollapsible(False)
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(5,5,5,5)
        self.table = QTableWidget(); self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "⏱️ TIME", "⚠️ LEVEL", "🔧 SERVICE", "📝 MESSAGE"])
        self.table.setColumnWidth(0, 45); self.table.setColumnWidth(1, 85); self.table.setColumnWidth(2, 85); self.table.setColumnWidth(3, 150)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        ll.addWidget(self.table); split.addWidget(left)

        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(5,5,5,5); rl.setSpacing(8)
        
        card1 = QFrame(); card1.setObjectName("Card"); c1l = QVBoxLayout(card1); c1l.setSpacing(8)
        lbl1 = QLabel("📊 ОБЩИЙ АНАЛИЗ"); lbl1.setStyleSheet("font-size: 15px; font-weight: bold; color: #58a6ff;")
        self.txt_global = QTextEdit(); self.txt_global.setReadOnly(True)
        self.txt_global.setPlaceholderText(self.t("welcome_global")); self.txt_global.setMinimumHeight(280)
        btn_row = QHBoxLayout()
        self.btn_global = QPushButton(self.t("btn_global")); self.btn_global.setEnabled(False)
        self.btn_global.setObjectName("AccentBtn"); self.btn_global.setFixedHeight(45)
        btn_row.addWidget(self.btn_global)
        self.timeline_lbl = QLabel(self.t("timeline"))
        self.timeline_lbl.setStyleSheet("padding: 8px; font-family: monospace; color: #8b949e; font-size: 11px;")
        self.timeline_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.timeline_lbl.setMinimumHeight(60)
        c1l.addWidget(lbl1); c1l.addWidget(self.txt_global, 1); c1l.addLayout(btn_row); c1l.addWidget(self.timeline_lbl)

        card2 = QFrame(); card2.setObjectName("Card"); c2l = QVBoxLayout(card2); c2l.setSpacing(8)
        lbl2 = QLabel("🔍 АНАЛИЗ СТРОКИ"); lbl2.setStyleSheet("font-size: 15px; font-weight: bold; color: #8b5cf6;")
        self.txt_line = QTextEdit(); self.txt_line.setReadOnly(True)
        self.txt_line.setPlaceholderText(self.t("welcome_line")); self.txt_line.setMinimumHeight(280)
        self.btn_line = QPushButton(self.t("btn_line")); self.btn_line.setEnabled(False)
        self.btn_line.setObjectName("AccentBtn"); self.btn_line.setFixedHeight(45)
        c2l.addWidget(lbl2); c2l.addWidget(self.txt_line, 1); c2l.addWidget(self.btn_line)

        rl.addWidget(card1, 5); rl.addWidget(card2, 4); split.addWidget(right); split.setSizes([900, 650])
        main.addWidget(split)

        self.sb = QStatusBar(); self.sb.showMessage("Готов | v5.0 by hero684k"); self.setStatusBar(self.sb)
        cw = QWidget(); cw.setLayout(main); self.setCentralWidget(cw)

    def connect_all(self):
        self.btn_open.clicked.connect(self.load_log); self.btn_export.clicked.connect(self.export)
        self.btn_clear.clicked.connect(self.clear); self.search.textChanged.connect(self.filter)
        self.combo_lang.currentTextChanged.connect(self.switch_lang)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.btn_global.clicked.connect(self.run_global_ai); self.btn_line.clicked.connect(self.run_line_ai)

    def load_log(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open log", "", "Logs (*.log *.txt);;All (*)")
        if not path: return
        self.table.setRowCount(0); self.txt_global.clear(); self.txt_line.clear()
        self.full_log = ""; self.selected_line = None
        self.btn_global.setEnabled(False); self.btn_line.setEnabled(False)
        self.status_lbl.setText(self.t("parsing")); self.progress.setValue(0)
        self.worker = ParserWorker(path)
        self.worker.row_ready.connect(self.add_row); self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self.on_done); self.worker.error.connect(self.on_err); self.worker.start()

    def add_row(self, d):
        r = self.table.rowCount()
        if r >= 100000: return
        self.table.insertRow(r)
        num = QTableWidgetItem(str(r+1)); num.setTextAlignment(Qt.AlignmentFlag.AlignCenter); num.setBackground(QColor("#161b22"))
        time_i = QTableWidgetItem(d['time']); time_i.setBackground(QColor("#161b22")); time_i.setData(Qt.ItemDataRole.UserRole, d['raw'])
        lvl_colors = {'CRITICAL': QColor("#ff4444"), 'ERROR': QColor("#ff6b6b"), 'WARNING': QColor("#ffd93d"), 'INFO': QColor("#8b949e")}
        bg_colors = {'CRITICAL': QColor("#3d1520"), 'ERROR': QColor("#2d1a1a"), 'WARNING': QColor("#2d2a15"), 'INFO': QColor("#161b22")}
        lvl_i = QTableWidgetItem(d['level']); lvl_i.setForeground(lvl_colors.get(d['level'], QColor("#8b949e")))
        lvl_i.setBackground(bg_colors.get(d['level'], QColor("#161b22"))); lvl_i.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        svc = QTableWidgetItem(d['service']); svc.setBackground(QColor("#161b22"))
        msg = QTableWidgetItem(d['msg']); msg.setBackground(QColor("#161b22"))
        self.table.setItem(r, 0, num); self.table.setItem(r, 1, time_i); self.table.setItem(r, 2, lvl_i)
        self.table.setItem(r, 3, svc); self.table.setItem(r, 4, msg)
        self.full_log += d['raw'] + "\n"; self.table.scrollToBottom()

    def on_done(self, data):
        self.analysis = data; self.status_lbl.setText(self.t("done"))
        self.btn_export.setEnabled(True); self.btn_global.setEnabled(True)
        self.sb.showMessage(f"✅ {data['total']} строк | {data['errors']} ошибок | {data['warns']} предупр.")
        try: self.txt_global.setHtml(SmartAI.global_analysis(self.full_log, data, self.lang))
        except Exception as e: self.txt_global.setHtml(f"<p style='color:#f85149;'>Ошибка: {e}</p>")
        tl = data.get('timeline', {})
        if tl:
            mx = max(tl.values()); lines = []
            for h in sorted(tl.keys()): c = tl[h]; bar = "█" * max(1, int((c/mx)*30)); lines.append(f"{h}:00 {bar} {c}")
            self.timeline_lbl.setText(f"⏱️ {self.t('timeline')}:\n" + "\n".join(lines[-10:]))

    def on_select(self):
        row = self.table.currentRow()
        if row < 0: return
        item = self.table.item(row, 1)
        if item:
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                self.selected_line = raw; self.btn_line.setEnabled(True)
                try: self.txt_line.setHtml(SmartAI.analyze_line(raw, self.full_log, self.lang))
                except Exception as e: self.txt_line.setHtml(f"<p style='color:#f85149;'>Ошибка: {e}</p>")

    def run_global_ai(self):
        if not self.analysis: return
        try: self.txt_global.setHtml(SmartAI.global_analysis(self.full_log, self.analysis, self.lang))
        except Exception as e: self.txt_global.setHtml(f"<p style='color:#f85149;'>Ошибка: {e}</p>")

    def run_line_ai(self):
        if not self.selected_line: return
        try: self.txt_line.setHtml(SmartAI.analyze_line(self.selected_line, self.full_log, self.lang))
        except Exception as e: self.txt_line.setHtml(f"<p style='color:#f85149;'>Ошибка: {e}</p>")

    def filter(self, text):
        s = text.lower()
        for r in range(self.table.rowCount()):
            h = True
            for c in range(self.table.columnCount()):
                i = self.table.item(r, c)
                if i and s in i.text().lower(): h = False; break
            self.table.setRowHidden(r, not h)

    def export(self):
        if not self.analysis: return
        path, _ = QFileDialog.getSaveFileName(self, "Export", "report.html", "HTML (*.html)")
        if path:
            with open(path, 'w', encoding='utf-8') as f: f.write(f"<h1>AI-LogPulse v5.0 Report</h1>\n{self.txt_global.toHtml()}")
            self.sb.showMessage(f"✅ Экспортировано: {path}")

    def clear(self):
        r = QMessageBox.question(self, "Очистить?", "Удалить все данные?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.table.setRowCount(0); self.txt_global.clear(); self.txt_line.clear()
            self.txt_global.setPlaceholderText(self.t("welcome_global")); self.txt_line.setPlaceholderText(self.t("welcome_line"))
            self.full_log = ""; self.selected_line = None; self.analysis = None
            self.progress.setValue(0); self.status_lbl.setText(self.t("ready"))
            self.btn_export.setEnabled(False); self.btn_global.setEnabled(False); self.btn_line.setEnabled(False)
            self.timeline_lbl.setText(self.t("timeline")); self.sb.showMessage("Готов")

    def switch_lang(self, lang):
        self.lang = lang
        self.btn_open.setText(self.t("open")); self.btn_export.setText(self.t("export")); self.btn_clear.setText(self.t("clear"))
        self.search.setPlaceholderText(self.t("search")); self.status_lbl.setText(self.t("ready"))
        self.btn_global.setText(self.t("btn_global")); self.btn_line.setText(self.t("btn_line")); self.timeline_lbl.setText(self.t("timeline"))
        if self.analysis:
            try: self.txt_global.setHtml(SmartAI.global_analysis(self.full_log, self.analysis, lang))
            except: pass
        if self.selected_line:
            try: self.txt_line.setHtml(SmartAI.analyze_line(self.selected_line, self.full_log, lang))
            except: pass

    def on_err(self, msg): self.status_lbl.setText(f"❌ {msg}"); QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    w = MainWindow(); w.show(); sys.exit(app.exec())