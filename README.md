# Jobzzzz

A Django project for scraping and managing job listings.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in the values.
4. Run database migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Notes

- The project uses PostgreSQL by default through `DATABASE_URL`.
- Celery uses `REDIS_URL` as the broker and result backend.
- Keep secrets in `.env`; do not commit that file.