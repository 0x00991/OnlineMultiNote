@echo off
echo Building..
pyinstaller -i NONE --add-data "note.html;." --add-data "favicon.ico;." --add-data "server.key;." --add-data "server.pem;." --noconfirm omn2.py