import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR.parent / "main_data.csv"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'crm.db'}")

app = FastAPI(title="CRM77")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
engine = create_engine(DATABASE_URL, future=True)


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    position: Mapped[str] = mapped_column(String(255), default="")
    contact_type: Mapped[str] = mapped_column(String(100), default="")
    work_phone: Mapped[str] = mapped_column(String(50), default="")
    mobile_phone: Mapped[str] = mapped_column(String(50), default="")
    work_email: Mapped[str] = mapped_column(String(255), default="")
    personal_email: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    interest_area: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company: Mapped[Optional[Company]] = relationship()


class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="new")
    scope: Mapped[str] = mapped_column(String(255), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    margin: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(String(500), default="")
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    company: Mapped[Company] = relationship()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    full_name: Mapped[str] = mapped_column(String(255), default="")


def migrate_sqlite_schema() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        contact_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(contacts)").fetchall()}
        deal_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(deals)").fetchall()}
        contact_add = {
            "work_email": "TEXT DEFAULT ''",
            "personal_email": "TEXT DEFAULT ''",
            "interest_area": "TEXT DEFAULT ''",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        }
        deal_add = {
            "started_at": "DATETIME",
            "scope": "TEXT DEFAULT ''",
            "cost": "FLOAT DEFAULT 0",
            "margin": "FLOAT DEFAULT 0",
            "finished_at": "DATETIME",
        }
        for col, ddl in contact_add.items():
            if col not in contact_cols:
                conn.exec_driver_sql(f"ALTER TABLE contacts ADD COLUMN {col} {ddl}")
        for col, ddl in deal_add.items():
            if col not in deal_cols:
                conn.exec_driver_sql(f"ALTER TABLE deals ADD COLUMN {col} {ddl}")


def get_or_create_company(session: Session, company_name: str) -> Optional[int]:
    clean = (company_name or "").strip()
    if not clean:
        return None
    company = session.scalar(select(Company).where(Company.name == clean))
    if company:
        return company.id
    company = Company(name=clean)
    session.add(company)
    session.flush()
    return company.id


def seed_from_csv() -> None:
    if not CSV_PATH.exists():
        return
    with Session(engine) as session:
        if session.scalar(select(func.count(Contact.id))) > 0:
            return
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                company_id = get_or_create_company(session, row.get("Компания", ""))
                session.add(
                    Contact(
                        external_id=int(row["ID"]) if (row.get("ID") or "").isdigit() else None,
                        first_name=(row.get("Имя") or "").strip(),
                        last_name=(row.get("Фамилия") or "").strip(),
                        company_id=company_id,
                        position=(row.get("Должность") or "").strip(),
                        contact_type=(row.get("Тип контакта") or "").strip(),
                        work_phone=(row.get("Рабочий телефон") or "").strip(),
                        mobile_phone=(row.get("Мобильный телефон") or "").strip(),
                        work_email=(row.get("Рабочий e-mail") or "").strip(),
                        source=(row.get("Источник") or "").strip(),
                    )
                )
        if not session.scalar(select(User).where(User.role == "admin")):
            session.add(User(email="admin@crm77.local", role="admin", full_name="System Admin"))
        session.commit()


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(engine)
    migrate_sqlite_schema()
    seed_from_csv()


@app.get("/")
def dashboard(request: Request):
    with Session(engine) as session:
        companies = session.execute(
            select(Company.id, Company.name, func.count(Contact.id).label("contacts_count"))
            .outerjoin(Contact, Contact.company_id == Company.id)
            .group_by(Company.id, Company.name)
            .order_by(func.count(Contact.id).desc(), Company.name.asc())
        ).all()
        contacts = session.execute(
            select(
                Contact.id,
                Contact.first_name,
                Contact.last_name,
                Contact.position,
                Contact.work_phone,
                Contact.mobile_phone,
                Contact.work_email,
                Company.name.label("company_name"),
            )
            .outerjoin(Company, Company.id == Contact.company_id)
            .order_by(Company.name.asc(), Contact.last_name.asc(), Contact.first_name.asc())
            .limit(120)
        ).all()
        deals = session.execute(
            select(
                Deal.id,
                Deal.title,
                Deal.amount,
                Deal.status,
                Deal.created_at,
                Company.name.label("company_name"),
            )
            .join(Company, Company.id == Deal.company_id)
            .order_by(Deal.created_at.desc())
            .limit(50)
        ).all()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "companies": companies, "contacts": contacts, "deals": deals},
        )


@app.get("/admin")
def admin_page(request: Request):
    with Session(engine) as session:
        users = session.execute(select(User).order_by(User.role.desc(), User.email.asc())).scalars().all()
        return templates.TemplateResponse("admin.html", {"request": request, "users": users})


@app.get("/contacts")
def contacts_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    q: str = Query(default=""),
):
    page_size = 50
    with Session(engine) as session:
        stmt = (
            select(
                Contact.id,
                Contact.first_name,
                Contact.last_name,
                Contact.position,
                Contact.work_phone,
                Contact.mobile_phone,
                Contact.work_email,
                Contact.source,
                Contact.updated_at,
                Company.name.label("company_name"),
            )
            .outerjoin(Company, Company.id == Contact.company_id)
            .order_by(Contact.updated_at.desc(), Contact.id.desc())
        )
        count_stmt = select(func.count(Contact.id))
        if q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                Contact.first_name.ilike(term)
                | Contact.last_name.ilike(term)
                | Contact.work_email.ilike(term)
                | Contact.mobile_phone.ilike(term)
                | Contact.work_phone.ilike(term)
                | Contact.source.ilike(term)
            )
            count_stmt = count_stmt.where(
                Contact.first_name.ilike(term)
                | Contact.last_name.ilike(term)
                | Contact.work_email.ilike(term)
                | Contact.mobile_phone.ilike(term)
                | Contact.work_phone.ilike(term)
                | Contact.source.ilike(term)
            )
        total = session.scalar(count_stmt) or 0
        pages = max((total + page_size - 1) // page_size, 1)
        safe_page = min(page, pages)
        contacts = session.execute(stmt.offset((safe_page - 1) * page_size).limit(page_size)).all()
        return templates.TemplateResponse(
            "contacts.html",
            {
                "request": request,
                "contacts": contacts,
                "page": safe_page,
                "pages": pages,
                "q": q,
                "total": total,
            },
        )


@app.get("/deals")
def deals_page(
    request: Request,
    page: int = Query(default=1, ge=1),
    q: str = Query(default=""),
    status: str = Query(default=""),
):
    page_size = 50
    with Session(engine) as session:
        stmt = (
            select(
                Deal.id,
                Deal.title,
                Deal.amount,
                Deal.status,
                Deal.scope,
                Deal.created_at,
                Company.name.label("company_name"),
            )
            .join(Company, Company.id == Deal.company_id)
            .order_by(Deal.created_at.desc(), Deal.id.desc())
        )
        count_stmt = select(func.count(Deal.id)).join(Company, Company.id == Deal.company_id)
        if q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(Deal.title.ilike(term) | Company.name.ilike(term) | Deal.scope.ilike(term))
            count_stmt = count_stmt.where(Deal.title.ilike(term) | Company.name.ilike(term) | Deal.scope.ilike(term))
        if status.strip():
            stmt = stmt.where(Deal.status == status.strip())
            count_stmt = count_stmt.where(Deal.status == status.strip())
        total = session.scalar(count_stmt) or 0
        pages = max((total + page_size - 1) // page_size, 1)
        safe_page = min(page, pages)
        deals = session.execute(stmt.offset((safe_page - 1) * page_size).limit(page_size)).all()
        return templates.TemplateResponse(
            "deals.html",
            {
                "request": request,
                "deals": deals,
                "page": safe_page,
                "pages": pages,
                "q": q,
                "status": status,
                "total": total,
            },
        )


@app.get("/companies/{company_id}")
def company_page(request: Request, company_id: int):
    with Session(engine) as session:
        company = session.get(Company, company_id)
        if not company:
            return RedirectResponse(url="/", status_code=303)
        contacts = session.execute(
            select(Contact)
            .where(Contact.company_id == company_id)
            .order_by(Contact.last_name.asc(), Contact.first_name.asc())
        ).scalars().all()
        deals = session.execute(
            select(Deal).where(Deal.company_id == company_id).order_by(Deal.created_at.desc())
        ).scalars().all()
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
    work_email: str = Form(""),
    personal_email: str = Form(""),
    source: str = Form(""),
):
    with Session(engine) as session:
        company_id = get_or_create_company(session, company_name)
        session.add(
            Contact(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                company_id=company_id,
                position=position.strip(),
                contact_type=contact_type.strip(),
                work_phone=work_phone.strip(),
                mobile_phone=mobile_phone.strip(),
                work_email=work_email.strip(),
                personal_email=personal_email.strip(),
                source=source.strip(),
            )
        )
        session.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/deals")
def create_deal(
    title: str = Form(...),
    company_name: str = Form(...),
    amount: float = Form(0),
    status: str = Form("new"),
    scope: str = Form(""),
    notes: str = Form(""),
):
    with Session(engine) as session:
        company_id = get_or_create_company(session, company_name)
        if not company_id:
            return RedirectResponse(url="/", status_code=303)
        session.add(
            Deal(
                title=title.strip(),
                company_id=company_id,
                amount=amount,
                status=status.strip(),
                scope=scope.strip(),
                notes=notes.strip(),
            )
        )
        session.commit()
    return RedirectResponse(url="/", status_code=303)
