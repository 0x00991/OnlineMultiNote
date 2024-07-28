from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import os
from getpass import getpass
import json
from tools import EncryptEngine, blank, sha2, checkncreatedir
import time
from threading import Thread
import secrets
import sys
from typing import Annotated
try:
    root_path = sys._MEIPASS
except:
    root_path = "."

checkncreatedir("notes")

if not os.path.isfile("settings.json"):
    WEB_PW = getpass("(WEB) Access code > ")
    WEB_AUTOSAVE = input("(WEB) Default Auto save? (y/any) > ") == "y"
    SAVEINTERVAL = 10
    MAXSIZE = 32*1024**2
    with open("settings.json", "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "web": {
                        "pw": WEB_PW,
                        "autosave": WEB_AUTOSAVE
                    },
                    "saveinterval": SAVEINTERVAL,
                    "maxsize": MAXSIZE
                },
                ensure_ascii=False
            )
        )
else:
    with open("settings.json", "r", encoding="utf-8") as f:
        fd = json.load(f)
        WEB_PW = fd["web"]["pw"]
        WEB_AUTOSAVE = fd["web"]["autosave"]
        SAVEINTERVAL = fd["saveinterval"]
        MAXSIZE = fd["maxsize"]

eengine = EncryptEngine(getpass("Enter File PW > "))

with open(f"{root_path}/note.html", "r", encoding="utf-8") as f:
    NOTE_HTML = f.read()


def HTMLResponse(body):
    return Response(content=body, media_type="text/html;charset=utf-8")

class AuthHandler(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.query_params.get("pass") != WEB_PW:
            if request.url.path != "/favicon.ico":
                return Response(content="", status_code=401)
        return await call_next(request)

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(AuthHandler)

@app.get("/")
def web_main(request: Request):
    ret = f"""<title>Main - OMN</title><input id="create" placeholder="Note Name"><input type="button" value="Go" onclick="location.href = '/'+document.getElementById('create').value+'?pass={WEB_PW}';"><br>"""
    for nn in os.listdir("notes/"):
        ret += f"""<a href="/{nn}?pass={WEB_PW}">/{nn}</a><br>"""
    return HTMLResponse(ret)

@app.get("/delete")
def web_delete(request: Request, note: str = None, session: str = None):
    if not note:
        return
    
    if session != NEWEST_SESSION.get(note, "--------"):
        return Response(content=f"Expired Session", status_code=208)

    if os.path.isfile(f"notes/{note}"):
        os.remove(f"notes/{note}")
    if CONTENTS.__contains__(note):
        del CONTENTS[note]
    if CONTENTS_SHA2.__contains__(note):
        del CONTENTS_SHA2[note]
        
    return RedirectResponse(url=f"/?pass={WEB_PW}")

BLACK_NAMES = ["'", "\"", "&", ";", "/", "<", ">", "*", ":", "|", "..", "main"]
@app.get("/{note}")
def web_getnote(request: Request, note: str):
    if note == "favicon.ico":
        return Response(content=favicon_file, media_type="image/x-icon")

    for bn in BLACK_NAMES:
        if note.find(bn) != -1:
            return RedirectResponse(url=f"/?pass={WEB_PW}")
        
    if not os.path.isfile(f"notes/{note}"):
        try:
            with open(f"notes/{note}", "wb") as f:
                f.write(b"")
        except:
            return RedirectResponse(url=f"/?pass={WEB_PW}")
        
    session = secrets.token_urlsafe(8)
    
    NEWEST_SESSION[note] = session
    
    return HTMLResponse(NOTE_HTML.replace("<<--note-->>", note)\
        .replace("<<--text-->>", readfile(note))\
        .replace("<<--pass-->>", WEB_PW)\
        .replace("<<--ischecked-->>", "checked" if WEB_AUTOSAVE else "")
        .replace("<<--session-->>", session)
        .replace("<<--note-->>", note)
    )



# 텍스트 파일 관리
CONTENTS = {}
CONTENTS_SHA2 = {}

def readfile(note):
    if not CONTENTS.__contains__(note):
        if not os.path.isfile(f"notes/{note}"):
            raise FileNotFoundError(f"notes/{note}")
        with open(f"notes/{note}", "rb") as f:
            content = f.read()
        
        if content == b"" or content == b"FirstOpen":
            CONTENTS[note] = ""
            
        else:
            CONTENTS[note] = eengine.decrypt(content).decode("utf-8")
        CONTENTS_SHA2[note] = sha2(CONTENTS[note])

    return CONTENTS[note]

def saver():
    while True:
        for k in CONTENTS.keys():
            if CONTENTS_SHA2[k] != sha2(CONTENTS[k]):
                force_save(k)
        time.sleep(SAVEINTERVAL)

def force_save(note):
    content = CONTENTS[note]
    if blank(content):
        with open(f"notes/{note}", "wb") as f:
            f.write(b"")
        print(f"[INFO] Note '{note}' Saved (Blank)")
    else:
        enc = eengine.encrypt(content.encode("utf-8"))
        eengine.write_file(f"notes/{note}", *enc)
        print(f"[INFO] Note '{note}' Saved.")
    CONTENTS_SHA2[note] = sha2(content)
    return "ok"

Thread(target=saver, daemon=True).start()

NEWEST_SESSION = {} # notename: SESSION

@app.post("/{note}")
def web_savenote(request: Request, note: str, session: str = None, autosave: str = None, text: Annotated[str, Form()] = None):
    global WEB_AUTOSAVE
    
    if note is None or not os.path.isfile(f"notes/{note}"):
        res = HTMLResponse("Error not found")
        res.status = 404
        return res
    start = time.time()

    
    if session != NEWEST_SESSION.get(note, "--------"):
        return Response(content=f"Expired Session", status_code=208)
    
    CONTENTS[note] = text
    WEB_AUTOSAVE = autosave == "true"
    
    end = time.time()
    return Response(content=f"{round((end-start)*1000, 2)}ms")

with open(os.path.join(root_path, "favicon.ico"), "rb") as f:
    favicon_file = f.read()

import uvicorn

ssl_options = {}
if os.path.isfile(f"{root_path}/server.key"):
    ssl_options["ssl_certfile"] = f"{root_path}/server.pem"
    ssl_options["ssl_keyfile"] = f"{root_path}/server.key"

uvicorn.run(app, host="0.0.0.0", port=2053, **ssl_options, ws_max_size=16*1000**2)
