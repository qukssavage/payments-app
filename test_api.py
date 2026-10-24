import os
import tempfile
from datetime import date, timedelta

# Отдельная временная база для тестов — задаём ДО импорта приложения
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest
from fastapi.testclient import TestClient

from database import get_connection
from main import app

client = TestClient(app)
THIS_MONTH = date.today().strftime("%Y-%m")


@pytest.fixture(autouse=True)
def clean_db():
    """Перед каждым тестом база пустая — тесты не влияют друг на друга."""
    conn = get_connection()
    conn.execute("DELETE FROM payments")
    conn.execute("DELETE FROM students")
    conn.commit()
    conn.close()


def create_student(fee=500000, name="Тест"):
    r = client.post("/students", json={
        "name": name, "phone": "+998901234567", "group_name": "G", "monthly_fee": fee,
    })
    assert r.status_code == 201
    return r.json()["id"]


def pay(student_id, amount, paid_at=None):
    body = {"student_id": student_id, "amount": amount}
    if paid_at:
        body["paid_at"] = paid_at
    r = client.post("/payments", json=body)
    assert r.status_code == 201


def debtors():
    r = client.get("/debtors", params={"month": THIS_MONTH})
    assert r.status_code == 200
    return {d["id"]: d for d in r.json()}


def test_student_without_payments_is_debtor():
    sid = create_student(fee=500000)
    result = debtors()
    assert result[sid]["paid"] == 0
    assert result[sid]["debt"] == 500000


def test_partial_payments_are_summed():
    sid = create_student(fee=500000)
    pay(sid, 200000)
    pay(sid, 100000)
    assert debtors()[sid]["debt"] == 200000


def test_fully_paid_and_overpaid_are_not_debtors():
    paid = create_student(fee=500000)
    overpaid = create_student(fee=500000)
    pay(paid, 500000)
    pay(overpaid, 700000)
    result = debtors()
    assert paid not in result
    assert overpaid not in result


def test_payment_from_previous_month_does_not_count():
    sid = create_student(fee=500000)
    last_day_prev_month = date.today().replace(day=1) - timedelta(days=1)
    pay(sid, 500000, paid_at=last_day_prev_month.isoformat())
    assert debtors()[sid]["debt"] == 500000


@pytest.mark.parametrize("bad_month", ["2026-13", "2026-1", "октябрь", "2026/10"])
def test_invalid_month_returns_422(bad_month):
    r = client.get("/debtors", params={"month": bad_month})
    assert r.status_code == 422


def test_delete_student_removes_payments():
    sid = create_student()
    pay(sid, 100000)
    assert client.delete(f"/students/{sid}").status_code == 204
    assert client.get(f"/students/{sid}/payments").status_code == 404

@pytest.mark.parametrize("bad_month", ["0000-01", "9999-12"])
def test_impossible_year_returns_422(bad_month):
    assert client.get("/debtors", params={"month": bad_month}).status_code == 422


def test_huge_amount_returns_422():
    r = client.post("/students", json={
        "name": "X", "phone": "+998901234567", "group_name": "G", "monthly_fee": 10**20,
    })
    assert r.status_code == 422