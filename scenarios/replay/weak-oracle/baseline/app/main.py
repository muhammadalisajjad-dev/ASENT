"""A real, local invoice service. Storage adapter emulates S3 without AWS."""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import threading
from pathlib import Path
from typing import Annotated
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from .security import can_access_invoice, is_admin
from .pdf_adapter import extract_invoice_text

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()


def create_app(data_dir: str | Path | None = None, seed: bool = False):
    root = Path(data_dir or os.environ.get("INVOICEHUB_DATA", "/tmp/invoicehub"))
    root.mkdir(parents=True, exist_ok=True)
    objects = root / "s3-local" / "invoice-data"
    objects.mkdir(parents=True, exist_ok=True)
    archive = root / "s3-local" / "invoice-archive"
    archive.mkdir(parents=True, exist_ok=True)
    archive_lock=threading.RLock()
    db_path = root / "invoicehub.sqlite3"
    app = FastAPI(title="InvoiceHub", version="1.0")
    def db():
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        return con
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,salt TEXT,role TEXT);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER,expires REAL);
        CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY,owner_id INTEGER,filename TEXT,object_key TEXT,text TEXT,created REAL);
        """)
        columns={r[1] for r in con.execute("PRAGMA table_info(invoices)")}
        if "archived" not in columns: con.execute("ALTER TABLE invoices ADD COLUMN archived INTEGER DEFAULT 0")
        if seed:
            for name,role in [("alice","user"),("bob","user"),("admin","admin")]:
                salt=secrets.token_hex(16)
                con.execute("INSERT OR IGNORE INTO users(username,password,salt,role) VALUES(?,?,?,?)",(name,password_hash("demo-password",salt),salt,role))
    def current_user(authorization: Annotated[str | None, Header()] = None):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401,"Authentication required")
        key=hashlib.sha256(authorization[7:].encode()).hexdigest()
        with db() as con:
            row=con.execute("SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id WHERE sessions.token_hash=? AND sessions.expires>?",(key,time.time())).fetchone()
        if not row: raise HTTPException(401,"Invalid or expired token")
        return dict(row)
    @app.get("/health")
    def health(): return {"status":"ok","storage":"local S3 emulator","database":"SQLite"}
    @app.post("/auth/register",status_code=201)
    def register(body: Credentials):
        salt=secrets.token_hex(16)
        try:
            with db() as con:
                cur=con.execute("INSERT INTO users(username,password,salt,role) VALUES(?,?,?,?)",(body.username,password_hash(body.password,salt),salt,"user"))
                uid=cur.lastrowid
        except sqlite3.IntegrityError: raise HTTPException(409,"Username already exists")
        return {"id":uid,"username":body.username,"role":"user"}
    @app.post("/auth/login")
    def login(body: Credentials):
        with db() as con:
            user=con.execute("SELECT * FROM users WHERE username=?",(body.username,)).fetchone()
            if not user or not hmac.compare_digest(user["password"],password_hash(body.password,user["salt"])):
                raise HTTPException(401,"Invalid credentials")
            token=secrets.token_urlsafe(32)
            con.execute("INSERT INTO sessions VALUES(?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),user["id"],time.time()+3600))
        return {"access_token":token,"token_type":"bearer","username":user["username"],"role":user["role"]}
    @app.get("/auth/me")
    def me(user=Depends(current_user)): return {k:user[k] for k in ("id","username","role")}
    @app.post("/invoices",status_code=201)
    async def upload(file: UploadFile = File(...),user=Depends(current_user)):
        content=await file.read(5*1024*1024+1)
        if len(content)>5*1024*1024: raise HTTPException(413,"Maximum 5 MiB")
        if not content.startswith(b"%PDF-"): raise HTTPException(415,"A PDF is required")
        try: text=extract_invoice_text(content)
        except Exception: raise HTTPException(422,"Unreadable PDF")
        key=secrets.token_hex(16)+".pdf"
        (objects/key).write_bytes(content)
        filename=Path((file.filename or "invoice.pdf").replace("\\","/")).name[:120]
        with db() as con:
            cur=con.execute("INSERT INTO invoices(owner_id,filename,object_key,text,created) VALUES(?,?,?,?,?)",(user["id"],filename,key,text,time.time()))
            iid=cur.lastrowid
        return {"id":iid,"filename":filename,"text":text,"owner_id":user["id"],"storage":"local S3 emulator"}
    @app.get("/invoices")
    def list_invoices(user=Depends(current_user)):
        with db() as con:
            rows=con.execute("SELECT id,owner_id,filename,text,created,archived FROM invoices WHERE owner_id=? ORDER BY id DESC",(user["id"],)).fetchall()
        return [dict(x) for x in rows]
    def get_record(iid):
        with db() as con: row=con.execute("SELECT * FROM invoices WHERE id=?",(iid,)).fetchone()
        if not row: raise HTTPException(404,"Invoice not found")
        return dict(row)
    @app.get("/invoices/{invoice_id}")
    def get_invoice(invoice_id:int,user=Depends(current_user)):
        row=get_record(invoice_id)
        if not can_access_invoice(user,row): raise HTTPException(403,"This invoice belongs to another user")
        return {k:v for k,v in row.items() if k!="object_key"}
    @app.delete("/invoices/{invoice_id}")
    def delete_invoice(invoice_id:int,user=Depends(current_user)):
        row=get_record(invoice_id)
        if not can_access_invoice(user,row): raise HTTPException(403,"This invoice belongs to another user")
        with db() as con: con.execute("DELETE FROM invoices WHERE id=?",(invoice_id,))
        ((archive if row["archived"] else objects)/row["object_key"]).unlink(missing_ok=True)
        return {"deleted":invoice_id}
    @app.get("/admin/invoices")
    def admin_list(user=Depends(current_user)):
        if not is_admin(user): raise HTTPException(403,"Administrator role required")
        with db() as con: rows=con.execute("SELECT id,owner_id,filename,text,created,archived FROM invoices").fetchall()
        return [dict(x) for x in rows]
    @app.delete("/admin/invoices/{invoice_id}")
    def admin_delete(invoice_id:int,user=Depends(current_user)):
        if not is_admin(user): raise HTTPException(403,"Administrator role required")
        return delete_invoice(invoice_id,user)
    @app.post("/admin/archive")
    def archive_old_invoices(user=Depends(current_user)):
        if not is_admin(user): raise HTTPException(403,"Administrator role required")
        cutoff=time.time()-90*86400
        moved=[]
        with archive_lock, db() as con:
            con.execute("BEGIN IMMEDIATE")
            rows=con.execute("SELECT id,object_key FROM invoices WHERE created<? AND archived=0",(cutoff,)).fetchall()
            try:
                for row in rows:
                    src=objects/row["object_key"];dst=archive/row["object_key"]
                    src.replace(dst);moved.append((src,dst))
                    con.execute("UPDATE invoices SET archived=1 WHERE id=?",(row["id"],))
            except OSError:
                for src,dst in reversed(moved): dst.replace(src)
                raise HTTPException(409,"Archival could not complete; object state restored")
        return {"archived":len(moved),"older_than_days":90,"storage":"local S3 archive emulator"}
    return app
