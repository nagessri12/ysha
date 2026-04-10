# Isha Social

A Django-based social platform with real-time features.

## Prerequisites

- Python 3.8+
- MySQL Server

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-github-repo-url>
   cd isha_project
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add your MySQL database credentials and secret key:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   MYSQL_DB=isha_social
   MYSQL_USER=your_username
   MYSQL_PASSWORD=your_password
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   ```

5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create Superuser (Optional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server:**
   ```bash
   python manage.py runserver
   ```
   Access the application at `http://127.0.0.1:8000/`.
