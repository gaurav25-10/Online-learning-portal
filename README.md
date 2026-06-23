# Online Learning Portal

BCA final year project built with HTML5, CSS3, Bootstrap 5, JavaScript, Python Flask, and SQLite.

The project also contains the older PHP/MySQL files, but the recommended backend now is Python Flask with SQLite. See [PYTHON_SETUP.md](PYTHON_SETUP.md).

## Features

- Student registration and login
- Admin login and dashboard
- Course CRUD with thumbnail uploads
- Student enrollment with duplicate prevention
- Course quizzes and result tracking
- Certificate generation for scores of 60% and above
- Responsive Bootstrap dashboard UI
- SQLite parameterized queries, password hashing, sessions, and basic sanitization

## Default Admin Login

- Email: `admin@portal.com`
- Password: `admin123`

The admin account is created automatically on the first admin login if it does not already exist.

## Python SQLite Setup

Follow [PYTHON_SETUP.md](PYTHON_SETUP.md).

## PHP Setup

1. Copy the project folder into your local server directory, for example:
   - XAMPP: `htdocs/online-learning-portal`
   - WAMP: `www/online-learning-portal`
2. Create a MySQL database named `online_learning_portal`.
3. Import [database/schema.sql](database/schema.sql).
4. Update database credentials in [config/database.php](config/database.php) if needed.
5. Start Apache and MySQL.
6. Open `http://localhost/online-learning-portal/`.

## Folder Structure

```text
online-learning-portal/
  admin/
  assets/
    css/
    images/
    js/
  config/
  database/
  includes/
  student/
  uploads/
  templates/
  app.py
  requirements.txt
  index.php
  login.php
  logout.php
  register.php
```
