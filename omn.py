from aiohttp import web
from aiohttp.web import Response, Request, HTTPTemporaryRedirect
import os
from getpass import getpass
import json
from tools import EncryptEngine, blank, sha2, checkncreatedir
import time
from threading import Thread

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

with open("./note.html", "r", encoding="utf-8") as f:
    NOTE_HTML = f.read()

def formathtml(notename, content):
    return NOTE_HTML.replace("<<--note-->>", notename)\
        .replace("<<--text-->>", content)\
        .replace("<<--pass-->>", WEB_PW)\
        .replace("<<--ischecked-->>", "checked" if WEB_AUTOSAVE else "")

def HTMLResponse(body):
    return Response(body=body, charset="utf-8", content_type="text/html")
@web.middleware
async def middleware(request: Request, handler):
    if request.rel_url.query.get("pass", None) != WEB_PW:
            return web.Response(body="", status=500)
        
    resp = await handler(request)
    
    return resp

app = web.Application(client_max_size=MAXSIZE, middlewares=[middleware])
routes = web.RouteTableDef()

@routes.get("/")
def web_main(request: Request):
    ret = f"""<input id="create" placeholder="Note Name"><input type="button" value="Go" onclick="location.href = '/'+document.getElementById('create').value+'?pass={WEB_PW}';"><br>"""
    for nn in os.listdir("notes/"):
        ret += f"""<a href="/{nn}?pass={WEB_PW}">/{nn}</a><br>"""
    return HTMLResponse(ret)

@routes.get("/delete")
def web_delete(request: Request):
    note = request.rel_url.query.get("note", None)
    if not note:
        return
    if os.path.isfile(f"notes/{note}"):
        os.remove(f"notes/{note}")
    if CONTENTS.__contains__(note):
        del CONTENTS[note]
    if CONTENTS_SHA2.__contains__(note):
        del CONTENTS_SHA2[note]
    return HTTPTemporaryRedirect(location=f"/?pass={WEB_PW}")

BLACK_NAMES = ["'", "\"", "&", ";", "/", "<", ">", "*", ":", "|", ".."]
@routes.get("/{note}")
def web_getnote(request: Request):
    note = request.match_info.get("note", None)
    if note is None:
        return HTTPTemporaryRedirect(location=f"/?pass={WEB_PW}")
    for bn in BLACK_NAMES:
        if note.find(bn) != -1:
            return HTTPTemporaryRedirect(location=f"/?pass={WEB_PW}")
    if not os.path.isfile(f"notes/{note}"):
        try:
            with open(f"notes/{note}", "wb") as f:
                f.write(b"")
        except:
            return HTTPTemporaryRedirect(location=f"/?pass={WEB_PW}")
    return HTMLResponse(formathtml(note, readfile(note)))



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

@routes.post("/{note}")
async def web_savenote(request: Request):
    global WEB_AUTOSAVE
    note = request.match_info.get("note", None)
    if note is None or not os.path.isfile(f"notes/{note}"):
        res = HTMLResponse("Error not found")
        res.status = 404
        return res
    start = time.time()
    
    post = await request.post()
    
    CONTENTS[note] = post["text"]
    WEB_AUTOSAVE = request.rel_url.query.get("autosave", None) == "true"
    
    end = time.time()
    return Response(body=f"{round((end-start)*1000, 2)}ms")

app.add_routes(routes)
web.run_app(app, host="0.0.0.0", port=2053)
