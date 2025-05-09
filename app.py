from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
from datetime import datetime
from flask import session, flash, redirect, url_for
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sip.db'
db = SQLAlchemy(app)
app.secret_key = 'cobayakyak'  # Bisa pakai random string


class SIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    email = db.Column(db.String(100))
    no_sip = db.Column(db.String(50))
    tanggal_terbit = db.Column(db.Date)
    tanggal_kadaluwarsa = db.Column(db.Date)
    sudah_dikirim = db.Column(db.Boolean, default=False)

@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    today = datetime.today().date()
    reminder_date = today + timedelta(days=180)

    if search_query:
        sips = SIP.query.filter(SIP.nama.ilike(f"%{search_query}%")).all()
    else:
        sips = SIP.query.all()

    akan_expired = SIP.query.filter(
    SIP.tanggal_kadaluwarsa <= datetime.utcnow() + timedelta(days=180)
).order_by(SIP.tanggal_kadaluwarsa.asc()).all()


    
    for sip in akan_expired:
        sisa_hari_total = (sip.tanggal_kadaluwarsa - today).days
        bulan = sisa_hari_total // 30
        hari = sisa_hari_total % 30
        sip.sisa_hari_format = f"{bulan} bulan {hari} hari lagi" if bulan > 0 else f"{hari} hari lagi"



    return render_template(
        'index.html',
        sips=sips,
        today=today,
        akan_expired=akan_expired
    )

    # Pastikan pengguna sudah login
    if 'logged_in' not in session:
        return redirect(url_for('login'))  # Jika belum login, arahkan ke halaman login
    
    # Lanjutkan dengan logika untuk menampilkan halaman index
    search_query = request.args.get('search', '').strip()
    today = datetime.today().date()
    reminder_date = today + timedelta(days=180)

    if search_query:
        sips = SIP.query.filter(SIP.nama.ilike(f"%{search_query}%")).all()
    else:
        sips = SIP.query.all()

    akan_expired = SIP.query.filter(
    SIP.tanggal_kadaluwarsa <= reminder_date,
    SIP.tanggal_kadaluwarsa > today
).order_by(SIP.tanggal_kadaluwarsa.asc()).all()



    
    for sip in akan_expired:
        sisa_hari_total = (sip.tanggal_kadaluwarsa - today).days
        bulan = sisa_hari_total // 30
        hari = sisa_hari_total % 30
        sip.sisa_hari_format = f"{bulan} bulan {hari} hari lagi" if bulan > 0 else f"{hari} hari lagi"

    return render_template(
        'index.html',
        sips=sips,
        today=today,
        akan_expired=akan_expired
    )



@app.route('/add', methods=['GET', 'POST'])
def add_sip():
    if request.method == 'POST':
        nama = request.form['nama']
        email = request.form['email']
        no_sip = request.form['no_sip']
        tanggal_terbit = datetime.strptime(request.form['tanggal_terbit'], '%Y-%m-%d')
        tanggal_kadaluwarsa = datetime.strptime(request.form['tanggal_kadaluwarsa'], '%Y-%m-%d')

        new_sip = SIP(
            nama=nama,
            email=email,
            no_sip=no_sip,
            tanggal_terbit=tanggal_terbit,
            tanggal_kadaluwarsa=tanggal_kadaluwarsa
        )
        db.session.add(new_sip)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_sip(id):
    sip = SIP.query.get_or_404(id)
    if request.method == 'POST':
        sip.nama = request.form['nama']
        sip.email = request.form['email']
        sip.no_sip = request.form['no_sip']
        sip.tanggal_terbit = datetime.strptime(request.form['tanggal_terbit'], '%Y-%m-%d')
        sip.tanggal_kadaluwarsa = datetime.strptime(request.form['tanggal_kadaluwarsa'], '%Y-%m-%d')
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', sip=sip)

@app.route('/delete/<int:id>')
def delete_sip(id):
    sip = SIP.query.get_or_404(id)
    db.session.delete(sip)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/trigger-notif')
def trigger_notif():
    force = request.args.get('force') == 'true'
    check_and_notify(force=force)
    return redirect(url_for('index'))

@app.route('/test-bot')
def test_bot():
    send_telegram(chat_id='430878024', message='Bot terhubung dan aktif! ✅')
    return 'Pesan dikirim.'


@app.route('/send-email-massal')
def send_email_massal():
    today = datetime.today().date()
    target_date = today + timedelta(days=180)

    sips = SIP.query.filter(
        SIP.tanggal_kadaluwarsa <= target_date,
        SIP.tanggal_kadaluwarsa > today
    ).all()

    count = 0
    for sip in sips:
        subject = "Pengingat: SIP Akan Kadaluarsa"
        body = (
            f"Yth. {sip.nama},\n\n"
            f"SIP Anda dengan nomor {sip.no_sip} akan kedaluwarsa pada {sip.tanggal_kadaluwarsa}.\n"
            f"Silakan lakukan perpanjangan tepat waktu.\n\n"
            f"Terima kasih."
        )
        if send_email(sip.email, subject, body):
            count += 1

    flash(f"Berhasil mengirim email ke {count} pengguna yang akan expired.", "success")
    return redirect(url_for('index'))


@app.route('/trigger-force-all')
def trigger_force_all():
    today = datetime.today().date()
    target_date = today + timedelta(days=180)

    sips = SIP.query.filter(
        SIP.tanggal_kadaluwarsa <= target_date,
        SIP.tanggal_kadaluwarsa > today
    ).all()

    for sip in sips:
        message = (
            f"🔔 Pengingat:\n"
            f"Nama: {sip.nama}\n"
            f"No. SIP: {sip.no_sip}\n"
            f"Akan kedaluwarsa pada: {sip.tanggal_kadaluwarsa}\n"
            f"Segera lakukan perpanjangan."
        )
        send_telegram(chat_id='430878024', message=message)
        sip.sudah_dikirim = True

    db.session.commit()
    return redirect(url_for('index'))

@app.route('/lihat_sip_akan_expired')
def lihat_sip_akan_expired():
    today = datetime.today().date()
    batas_expired = today + timedelta(days=30)
    
    conn = sqlite3.connect('sip.db')
    c = conn.cursor()
    c.execute("SELECT * FROM sip")
    data = c.fetchall()
    conn.close()

    expired_list = []
    for row in data:
        tanggal_kadaluwarsa = datetime.strptime(row[5], "%Y-%m-%d").date()
        if today <= tanggal_kadaluwarsa <= batas_expired:
            sisa_hari = (tanggal_kadaluwarsa - today).days
            expired_list.append({
                'nama': row[1],
                'email': row[2],
                'no_sip': row[3],
                'tanggal_terbit': row[4],
                'tanggal_kadaluwarsa': row[5],
                'sisa_hari': sisa_hari  # ← tambahin ini
            })

    return render_template('expired.html', expired_list=expired_list)

from flask import session, flash, redirect, url_for

# Route untuk halaman login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Ambil data dari form login
        username = request.form['username']
        password = request.form['password']

        # Validasi login (bisa hardcode atau dari database)
        if username == 'admin' and password == 'password':  # Ganti sesuai dengan autentikasi yang kamu inginkan
            session['logged_in'] = True  # Menandakan pengguna sudah login
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))  # Redirect ke halaman index setelah login
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')  # Render halaman login jika GET request

@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Hapus session 'logged_in'
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))  # Redirect ke halaman login setelah logout





def send_email(to, subject, body):
    sender_email = "amawibaww@gmail.com"
    sender_password = "zrdj vabq cesn ptda"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email error:", e)
        return False


@app.route('/upload-excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nama file kosong', 'error')
        return redirect(url_for('index'))

    # Cek ekstensi file (tanpa secure_filename)
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('Format file harus .xlsx atau .xls', 'error')
        return redirect(url_for('index'))

    try:
        # Baca file langsung dari memory
        df = pd.read_excel(file)
        count = 0

        for _, row in df.iterrows():
            # Validasi data
            if not all(col in row for col in ['nama', 'email', 'no_sip', 'tanggal_terbit', 'tanggal_kadaluwarsa']):
                flash('Kolom wajib: nama, email, no_sip, tanggal_terbit, tanggal_kadaluwarsa', 'error')
                break

            new_sip = SIP(
                nama=row['nama'],
                email=row['email'],
                no_sip=row['no_sip'],
                tanggal_terbit = pd.to_datetime(row['tanggal_terbit']).date(),
                tanggal_kadaluwarsa = pd.to_datetime(row['tanggal_kadaluwarsa']).date()
            )
            db.session.add(new_sip)
            count += 1

        db.session.commit()
        flash(f'Berhasil upload {count} data SIP!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Gagal memproses file: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/send-rekap-expired')
def send_rekap_expired():
    today = datetime.today().date()
    batas_expired = today + timedelta(days=180)

    sips = SIP.query.filter(
    SIP.tanggal_kadaluwarsa.between(today, batas_expired)
).order_by(SIP.tanggal_kadaluwarsa.asc()).all()


    if not sips:
        flash("✅ Tidak ada SIP yang akan expired dalam 6 bulan ke depan.", "info")
        return redirect(url_for('index'))

    # Buat tabel HTML
    rows = ""
    for sip in sips:
        sisa_hari = (sip.tanggal_kadaluwarsa - today).days
        bulan = sisa_hari // 30
        hari = sisa_hari % 30
        sisa_text = f"{bulan} bulan {hari} hari lagi" if bulan > 0 else f"{hari} hari lagi"

        rows += f"""
        <tr>
            <td>{sip.nama}</td>
            <td>{sip.no_sip}</td>
            <td>{sip.tanggal_kadaluwarsa}</td>
            <td>{sisa_text}</td>
        </tr>
        """

    html_body = f"""
    <html>
    <body>
        <p>📋 Berikut daftar SIP yang akan expired:</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
            <thead>
                <tr>
                    <th>Nama</th>
                    <th>No SIP</th>
                    <th>Tanggal Expired</th>
                    <th>Sisa Waktu</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <p>Harap segera ditindaklanjuti.</p>
    </body>
    </html>
    """

    send_email_html("abieperdanakusuma@gmail.com", "Rekap SIP Akan Expired", html_body)
    flash("📧 Email rekap (dalam bentuk tabel) berhasil dikirim ke admin.", "success")
    return redirect(url_for('index'))




def send_telegram(chat_id, message):
    TOKEN = '7614554370:AAFsoKR5UG-GLKHSUzM8Jwr63Ju8Oz1ebeQ'
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    response = requests.post(url, data=payload)
    print(response.text)  # DEBUG
    return response.status_code == 200 and response.json().get('ok') == True


def check_and_notify(force=False):
    today = datetime.today().date()
    target_date = today + timedelta(days=180)

    filter_criteria = [
        SIP.tanggal_kadaluwarsa <= target_date,
        SIP.tanggal_kadaluwarsa > today
    ]
    if not force:
        filter_criteria.append(SIP.sudah_dikirim == False)

    sips = SIP.query.filter(*filter_criteria).all()

    print(f"Jumlah data yang akan dikirim: {len(sips)}")
    for sip in sips:
        print(f"Kirim ke: {sip.nama}, Expired: {sip.tanggal_kadaluwarsa}, Sudah Dikirim: {sip.sudah_dikirim}")
        message = (
            f"🔔 Pengingat:\n"
            f"Nama: {sip.nama}\n"
            f"No. SIP: {sip.no_sip}\n"
            f"Akan kedaluwarsa pada: {sip.tanggal_kadaluwarsa}\n"
            f"Segera lakukan perpanjangan."
        )
        success = send_telegram(chat_id='430878024', message=message)
        if success and not sip.sudah_dikirim:
            sip.sudah_dikirim = True
            db.session.commit()
        elif not success:
            print("❌ Gagal kirim ke Telegram")


def send_email_html(to, subject, html_body):
    sender_email = "amawibaww@gmail.com"
    sender_password = "zrdj vabq cesn ptda"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email error:", e)
        return False



if __name__ == '__main__':
    app.run(debug=True)
