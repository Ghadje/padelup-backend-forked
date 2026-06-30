# Running the PadelUp Backend

This is a Python Django backend built using the Django REST Framework (DRF) with SQLite as the default local database.

---

## Prerequisites

- **Python 3.11+**
- **pip** (Python package installer)

---

## Getting Started

### 1. Set Up the Virtual Environment

A virtual environment (`venv`) is already included in the project directory. You need to activate it:

- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

*If the virtual environment is missing or needs recreating, you can create it using:*
```bash
python -m venv venv
```

### 2. Install Dependencies

Once the virtual environment is activated, install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Database Migrations

Apply the database migrations to set up the local SQLite database (`db.sqlite3`):

```bash
python manage.py migrate
```

### 4. Create a Superuser (Optional)

To access the Django Admin panel, create an administrator account:

```bash
python manage.py createsuperuser
```
Follow the prompts to enter a username, email, and password.

### 5. Seed Sample Data (Optional)

There are scripts and custom management commands available to seed the database with sample data.

#### Seed Clubs & Stats:
- **Sample Clubs:**
  ```bash
  python add_sample_clubs.py
  ```
- **Tunisia Clubs:**
  ```bash
  python add_tunisia_club.py
  ```
- **Player Stats:**
  ```bash
  python create_player_stats.py
  ```

#### Custom Django Commands:
- **Test Bookings:**
  ```bash
  python manage.py create_test_bookings
  ```
- **Test Matches:**
  ```bash
  python manage.py create_test_matches
  ```
- **Fix Match Statuses:**
  ```bash
  python manage.py fix_match_statuses
  ```
- **Recalculate Stats:**
  ```bash
  python manage.py recalculate_stats
  ```

---

## Running the Server

Start the Django local development server:

```bash
python manage.py runserver
```

By default, the server will run at:
- **API URL:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Panel:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Environment Variables (Optional)

The application has default fallbacks for local development, but you can override them via environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DEBUG` | Enable/disable debug mode | `True` |
| `SECRET_KEY` | Django secret key | A default insecure key |
| `DATABASE_URL` | PostgreSQL connection string | Uses SQLite (`db.sqlite3`) if empty |
| `ALLOWED_HOSTS` | Allowed host headers | `localhost,127.0.0.1` |
| `EMAIL_HOST` | SMTP server for emails | `smtp.resend.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | SMTP TLS encryption | `True` |
| `EMAIL_HOST_USER` | SMTP username | Empty |
| `EMAIL_HOST_PASSWORD`| SMTP password | Empty |
| `DEFAULT_FROM_EMAIL` | Default sender email address| `noreply@padelup.com` |

---

## Production Deployment

This project is configured for deployment on platforms like Render or Railway.
- Build Script: `build.sh` (runs `pip install`, `collectstatic`, and `migrate`).
- Web Server: Runs using **Gunicorn** (`gunicorn backend.wsgi:application`).
- Configuration: See `render.yaml` or `Procfile`.
