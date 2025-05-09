from app import db, app, SIP
from datetime import datetime

with app.app_context():
    user1 = SIP(
        nama="Andi",
        email="andi@example.com",
        no_sip="SIP001",
        tanggal_terbit=datetime.strptime("2023-01-01", "%Y-%m-%d").date(),
        tanggal_kadaluwarsa=datetime.strptime("2025-01-01", "%Y-%m-%d").date()
    )

    user2 = SIP(
        nama="Budi",
        email="budi@example.com",
        no_sip="SIP002",
        tanggal_terbit=datetime.strptime("2023-06-01", "%Y-%m-%d").date(),
        tanggal_kadaluwarsa=datetime.strptime("2025-06-01", "%Y-%m-%d").date()
    )

    db.session.add_all([user1, user2])
    db.session.commit()
    print("Data berhasil ditambahkan.")
