# Run The Python SQLite Backend

This version does **not** need XAMPP, MySQL, phpMyAdmin, or any database installation.

It uses:

- Python 3
- Flask
- SQLite
- Bootstrap 5

SQLite will automatically create this database file:

```text
online_learning_portal.db
```

## 1. Open PowerShell

Run:

```powershell
cd "C:\Users\Asus\Desktop\kothiyal (OLP)"
```

## 2. Install Dependencies

Run:

```powershell
python -m pip install -r requirements.txt
```

## 3. Start The Project

Run:

```powershell
python app.py
```

You should see something like:

```text
Running on http://127.0.0.1:5000
```

Open this in your browser:

```text
http://127.0.0.1:5000
```

## Admin Login

```text
Email: admin@portal.com
Password: admin123
```

The admin account, sample courses, quiz questions, and database tables are created automatically.

## If It Still Does Not Run

Make sure Flask is installed:

```powershell
python -m pip install Flask Werkzeug
```

Then run again:

```powershell
python app.py
```
