import csv
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "crm.db"
CSV_PATH = BASE_DIR.parent / "CONTACT_20250916_5299b658_68c9c36edbc7d.csv"

app = FastAPI(title="CRM Contacts & Deals")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            company_id INTEGER,
            position TEXT,
            contact_type TEXT,
            work_phone TEXT,
            mobile_phone TEXT,
            email TEXT,
            source TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'new',
            company_id INTEGER NOT NULL,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_or_create_company(cur: sqlite3.Cursor, name: str) -> Optional[int]:
    cleaned = (name or "").strip()
    if not cleaned:
        return None
    cur.execute("SELECT id FROM companies WHERE name = ?", (cleaned,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur.execute("INSERT INTO companies(name) VALUES (?)", (cleaned,))
    return cur.lastrowid


def seed_from_csv() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM contacts")
    if cur.fetchone()["total"] > 0:
        conn.close()
        return
    if not CSV_PATH.exists():
        conn.close()
        return
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            company_id = get_or_create_company(cur, row.get("Компания", ""))
            cur.execute(
                """
                INSERT INTO contacts(
                    external_id, first_name, last_name, company_id, position,
                    contact_type, work_phone, mobile_phone, email, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["ID"]) if (row.get("ID") or "").isdigit() else None,
                    row.get("Имя", "").strip(),
                    row.get("Фамилия", "").strip(),
                    company_id,
                    row.get("Должность", "").strip(),
                    row.get("Тип контакта", "").strip(),
                    row.get("Рабочий телефон", "").strip(),
                    row.get("Мобильный телефон", "").strip(),
                    row.get("Рабочий e-mail", "").strip(),
                    row.get("Источник", "").strip(),
                ),
            )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    seed_from_csv()


@app.get("/")
def dashboard(request: Request):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.id, c.name, COUNT(ct.id) AS contacts_count
        FROM companies c
        LEFT JOIN contacts ct ON ct.company_id = c.id
        GROUP BY c.id
        ORDER BY contacts_count DESC, c.name ASC
        """
    )
    companies = cur.fetchall()
    cur.execute(
        """
        SELECT ct.id, ct.first_name, ct.last_name, ct.position, ct.work_phone,
               ct.mobile_phone, ct.email, cp.name AS company_name
        FROM contacts ct
        LEFT JOIN companies cp ON cp.id = ct.company_id
        ORDER BY cp.name ASC, ct.last_name ASC, ct.first_name ASC
        """
    )
    contacts = cur.fetchall()
    cur.execute(
        """
        SELECT d.id, d.title, d.amount, d.status, d.created_at, c.name AS company_name
        FROM deals d
        JOIN companies c ON c.id = d.company_id
        ORDER BY d.created_at DESC
        LIMIT 50
        """
    )
    deals = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "companies": companies, "contacts": contacts, "deals": deals},
    )


@app.get("/companies/{company_id}")
def company_page(request: Request, company_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM companies WHERE id = ?", (company_id,))
    company = cur.fetchone()
    if not company:
        conn.close()
        return RedirectResponse(url="/", status_code=303)
    cur.execute(
        """
        SELECT id, first_name, last_name, position, contact_type,
               work_phone, mobile_phone, email, source
        FROM contacts
        WHERE company_id = ?
        ORDER BY last_name ASC, first_name ASC
        """,
        (company_id,),
    )
    contacts = cur.fetchall()
    cur.execute(
        """
        SELECT id, title, amount, status, notes, created_at
        FROM deals
        WHERE company_id = ?
        ORDER BY created_at DESC
        """,
        (company_id,),
    )
    deals = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(
        "company.html",
        {"request": request, "company": company, "contacts": contacts, "deals": deals},
    )


@app.post("/contacts")
def create_contact(
    first_name: str = Form(...),
    last_name: str = Form(""),
    company_name: str = Form(""),
    position: str = Form(""),
    contact_type: str = Form(""),
    work_phone: str = Form(""),
    mobile_phone: str = Form(""),
    email: str = Form(""),
    source: str = Form(""),
):
    conn = get_conn()
    cur = conn.cursor()
    company_id = get_or_create_company(cur, company_name)
    cur.execute(
        """
        INSERT INTO contacts(
            first_name, last_name, company_id, position, contact_type,
            work_phone, mobile_phone, email, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (first_name, last_name, company_id, position, contact_type, work_phone, mobile_phone, email, source),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.post("/deals")
def create_deal(
    title: str = Form(...),
    company_name: str = Form(...),
    amount: float = Form(0),
    status: str = Form("new"),
    notes: str = Form(""),
):
    conn = get_conn()
    cur = conn.cursor()
    company_id = get_or_create_company(cur, company_name)
    if not company_id:
        conn.close()
        return RedirectResponse(url="/", status_code=303)
    cur.execute(
        "INSERT INTO deals(title, amount, status, company_id, notes) VALUES (?, ?, ?, ?, ?)",
        (title, amount, status, company_id, notes),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
