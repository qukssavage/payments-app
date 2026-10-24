from typing import List

from fastapi import Depends, FastAPI, HTTPException

from database import get_db, init_db
from schemas import Debtor, Payment, PaymentCreate, Student, StudentCreate, StudentUpdate

from datetime import date
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

init_db()

app = FastAPI(title="Учёт оплат учебного центра")


def get_student_or_404(db, student_id: int):
    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    return dict(row)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/students", response_model=Student, status_code=201)
def create_student(data: StudentCreate, db=Depends(get_db)):
    cur = db.execute(
        "INSERT INTO students (name, phone, group_name, monthly_fee) VALUES (?, ?, ?, ?)",
        (data.name, data.phone, data.group_name, data.monthly_fee),
    )
    db.commit()
    return get_student_or_404(db, cur.lastrowid)


@app.get("/students", response_model=List[Student])
def list_students(db=Depends(get_db)):
    rows = db.execute("SELECT * FROM students ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int, db=Depends(get_db)):
    return get_student_or_404(db, student_id)


@app.patch("/students/{student_id}", response_model=Student)
def update_student(student_id: int, data: StudentUpdate, db=Depends(get_db)):
    get_student_or_404(db, student_id)
    fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if fields:
        set_clause = ", ".join(f"{key} = ?" for key in fields)
        db.execute(
            f"UPDATE students SET {set_clause} WHERE id = ?",
            (*fields.values(), student_id),
        )
        db.commit()
    return get_student_or_404(db, student_id)


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, db=Depends(get_db)):
    get_student_or_404(db, student_id)
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()

@app.post("/payments", response_model=Payment, status_code=201)
def create_payment(data: PaymentCreate, db=Depends(get_db)):
    get_student_or_404(db, data.student_id)
    cur = db.execute(
        "INSERT INTO payments (student_id, amount, paid_at) VALUES (?, ?, ?)",
        (data.student_id, data.amount, data.paid_at.isoformat()),
    )
    db.commit()
    row = db.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/students/{student_id}/payments", response_model=List[Payment])
def list_student_payments(student_id: int, db=Depends(get_db)):
    get_student_or_404(db, student_id)
    rows = db.execute(
        "SELECT * FROM payments WHERE student_id = ? ORDER BY paid_at, id",
        (student_id,),
    ).fetchall()
    return [dict(r) for r in rows]

def month_bounds(month: str):
    """'2026-10' -> ('2026-10-01', '2026-11-01'): начало месяца и начало следующего."""
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start.isoformat(), end.isoformat()


@app.get("/debtors", response_model=List[Debtor])
def get_debtors(
    month: Optional[str] = Query(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Месяц в формате YYYY-MM. По умолчанию текущий.",
        examples=["2026-10"],
    ),
    db=Depends(get_db),
):
    if month is None:
        month = date.today().strftime("%Y-%m")
    start, end = month_bounds(month)

    rows = db.execute(
        """
        SELECT s.id, s.name, s.phone, s.group_name, s.monthly_fee,
               COALESCE(SUM(p.amount), 0)                 AS paid,
               s.monthly_fee - COALESCE(SUM(p.amount), 0) AS debt
        FROM students s
        LEFT JOIN payments p
               ON p.student_id = s.id
              AND p.paid_at >= ? AND p.paid_at < ?   -- фильтр в ON, а не в WHERE!
        WHERE s.created_at < ?                       -- ученик уже был в этом месяце
        GROUP BY s.id
        HAVING debt > 0
        ORDER BY debt DESC, s.name
        """,
        (start, end, end),
    ).fetchall()
    return [dict(r) for r in rows]