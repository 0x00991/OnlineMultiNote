@echo off
echo Building..
pyinstaller -i NONE --add-data "note.html;." --noconfirm omn.py