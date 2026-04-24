#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Объединение телемаркетинг-рассылки с контактами из основных баз."""

import csv
import re
from pathlib import Path

BASE = Path(__file__).parent

def norm_phone(s):
    """Нормализация телефона — только цифры, последние 10 или 11."""
    if not s: return ""
    d = re.sub(r"\D", "", str(s))
    return d[-10:] if len(d) >= 10 else d  # последние 10 цифр

def norm_email(s):
    return (s or "").strip().lower()

def is_email(s):
    return bool(re.match(r"^[\w.+-]+@[\w.-]+\.[a-z]{2,}$", (s or "").strip(), re.I))

def parse_contact_field(text):
    """Парсинг колонки 'Имя и куда писать': извлечь имя, телефон, email."""
    if not text or not str(text).strip():
        return "", "", ""
    text = " ".join(str(text).split())
    name, phone, email = "", "", ""
    # Email
    em = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", text, re.I)
    if em:
        email = em.group(0)
        text = text[:em.start()] + " " + text[em.end():]
    # Телефон (7/8 + цифры, пробелы, скобки, дефисы)
    ph = re.search(r"[78][\s\-()]*\d[\s\-()\d]{8,}", text)
    if ph:
        phone = norm_phone(ph.group(0))
        text = text[:ph.start()] + " " + text[ph.end():]
    # Международные номера
    if not phone and re.search(r"\d{10,}", text):
        m = re.search(r"\d{10,}", text)
        if m and len(m.group(0)) >= 10:
            phone = norm_phone(m.group(0))
    # Имя — оставшийся текст до email/phone, первое слово или два
    rest = re.sub(r"\s+", " ", text).strip()
    rest = re.sub(r"[\s/]+$", "", rest)
    words = rest.split()
    rus = [w for w in words if re.search(r"[а-яёА-ЯЁ]", w)]
    name = " ".join(rus[:3]) if rus else rest.split()[0] if words else ""
    return name.strip(), phone, email

def load_contacts_main():
    """CONTACT — основная база клиентов."""
    lookup_phone, lookup_email = {}, {}
    with open(BASE / "CONTACT_20250916_5299b658_68c9c36edbc7d.csv", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            c = row.get("Компания", "").strip()
            name = f"{row.get('Имя','')} {row.get('Фамилия','')}".strip()
            pos = row.get("Должность", "").strip()
            for ph in [row.get("Рабочий телефон",""), row.get("Мобильный телефон","")]:
                k = norm_phone(ph)
                if k and k not in lookup_phone:
                    lookup_phone[k] = {"company": c, "name": name, "position": pos}
            em = norm_email(row.get("Рабочий e-mail",""))
            if em and em not in lookup_email:
                lookup_email[em] = {"company": c, "name": name, "position": pos}
    return lookup_phone, lookup_email

def load_hr():
    """База HR — контакты с конференций."""
    lookup_phone, lookup_email = {}, {}
    with open(BASE / "База с нашими HRами - CONTACT_20250409_d3e509db_67f68982bf1bc.csv", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            c = row.get("Компания", "").strip()
            name = f"{row.get('Имя','')} {row.get('Фамилия','')}".strip()
            pos = row.get("Должность", "").strip()
            k = norm_phone(row.get("Рабочий телефон",""))
            if k and k not in lookup_phone:
                lookup_phone[k] = {"company": c, "name": name, "position": pos}
            em = norm_email(row.get("Рабочий e-mail","") or "")
            if em and em not in lookup_email:
                lookup_email[em] = {"company": c, "name": name, "position": pos}
    return lookup_phone, lookup_email

def load_telemarketing_base():
    """База контактов с телефонами (не с конференций)."""
    lookup_phone, lookup_email = {}, {}
    with open(BASE / "База всех контактов с телефонами (не с конференций) - CONTACT_20250416_5a41250b_67ffb05f5de4f.csv", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            c = row.get("Компания", "").strip()
            name = f"{row.get('Имя','')} {row.get('Фамилия','')}".strip()
            pos = row.get("Должность", "").strip()
            k = norm_phone(row.get("Рабочий телефон",""))
            if k and k not in lookup_phone:
                lookup_phone[k] = {"company": c, "name": name, "position": pos}
            em = norm_email(row.get("Рабочий e-mail","") or "")
            if em and em not in lookup_email:
                lookup_email[em] = {"company": c, "name": name, "position": pos}
    return lookup_phone, lookup_email

def merge_lookups(*pairs):
    ph, em = {}, {}
    for p, e in pairs:
        ph.update(p)
        em.update(e)
    return ph, em

def main():
    ph_main, em_main = load_contacts_main()
    ph_hr, em_hr = load_hr()
    ph_tm, em_tm = load_telemarketing_base()
    lookup_phone, lookup_email = merge_lookups(
        (ph_main, em_main), (ph_hr, em_hr), (ph_tm, em_tm)
    )

    # Ключевые слова для приоритета прозвона (позитивная реакция)
    pos = ["преза", "презу", "встреча", "интерес", "передал", "перезвон", "инфо", "нужна инф", "оправлена", "кп", "каталог"]
    neg = ["не звонить", "неактуально", "не нужны", "спасибо не надо", "нет задач", "нет бюджета", "конкурент"]

    out_rows = []
    seen = set()

    with open(BASE / "Телемаркетинг рассылка - Отправка сообщений.csv", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            link = (row.get("Ссылка на компанию в Битрикс24") or "").strip()
            raw = (row.get("Имя и куда писать") or "").strip()
            st25 = (row.get("Статус клиента 2025") or "").strip()
            st26 = (row.get("Статус клиента 2026") or "").strip()
            status = (row.get("Статус  )ОБНОВИТЬ(") or row.get("Статус  )ОБНОВИТЬ(", "") or "").strip()
            comm = (row.get("Комментарии") or "").strip()
            name, phone, email = parse_contact_field(raw)

            if not phone and not email:
                continue
            key = (norm_phone(phone) or "", norm_email(email) or "")
            if key in seen or key == ("", ""):
                continue
            seen.add(key)

            company, full_name, position = "", "", ""
            if phone:
                info = lookup_phone.get(norm_phone(phone))
                if info:
                    company, full_name = info["company"], info["name"]
                    position = info.get("position", "")
            if (not company or not full_name) and email:
                info = lookup_email.get(norm_email(email))
                if info:
                    company = company or info["company"]
                    full_name = full_name or info["name"]
                    position = position or info.get("position", "")

            name_display = full_name or name or raw.split()[0] if raw else ""

            txt = f"{st25} {st26} {comm}".lower()
            prio = "Высокий" if any(p in txt for p in pos) and not any(n in txt for n in neg) else "Средний"
            if any(n in txt for n in neg):
                prio = "Низкий"

            out_rows.append({
                "Имя": name_display.split()[0] if name_display else name,
                "Фамилия": " ".join(name_display.split()[1:]) if name_display and len(name_display.split()) > 1 else "",
                "Компания": company,
                "Должность": position,
                "Телефон": phone,
                "Email": email,
                "Статус_рассылки": status,
                "Статус_2025": st25,
                "Статус_2026": st26,
                "Комментарии": comm,
                "Приоритет_прозвона": prio,
            })

    out_path = BASE / "Единая_таблица_для_прозвона.csv"
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Имя", "Фамилия", "Компания", "Должность", "Телефон", "Email", "Статус_рассылки", "Статус_2025", "Статус_2026", "Комментарии", "Приоритет_прозвона"])
        w.writeheader()
        w.writerows(out_rows)

    print(f"Готово: {out_path}")
    print(f"Записей: {len(out_rows)}")
    high = sum(1 for r in out_rows if r["Приоритет_прозвона"] == "Высокий")
    print(f"Приоритет «Высокий» (позитивная реакция): {high}")

if __name__ == "__main__":
    main()
