# Radar Mikro-nisz - IT Job Market Analysis

Multi-page Streamlit application for analyzing IT job market niches and mainstream opportunities in the Polish IT labor market.

## 🚀 Quick Start

### Prerequisites
- Docker installed and running
- Git

### Setup & Run

1. Clone the repository.
2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
3. Start the application:
   ```bash
   docker-compose up --build
   ```
4. Open the app in your browser:
   ```text
   http://localhost:8501
   ```

### Notes
- Source code changes are mounted into the container and should reload automatically.
- If the app does not restart cleanly, stop containers and run `docker-compose down` before starting again.

## 🛠️ Common Commands

```bash
# Start application
docker-compose up --build

# Stop application
docker-compose down

# View logs
docker-compose logs -f streamlit-app

# Open an interactive shell inside the app container
docker-compose exec streamlit-app /bin/bash

# Run the scraper from inside the app container
docker-compose exec streamlit-app python -c "from scrapers.scraper_manager import ScraperManager; ScraperManager().run_all()"

# Install dependencies inside container
docker-compose exec streamlit-app pip install -r requirements.txt
```

## 📁 Project Structure

```
.
├── app.py                 # Streamlit entry point
├── pages/                 # Streamlit application pages
│   ├── 1_Home.py
│   ├── 2_Konkurencja.py
│   ├── 3_Regresja.py
│   ├── 4_Kalkulator_ROI.py
│   └── 5_Metodologia.py
├── scrapers/              # Scraper manager and source scrapers
│   ├── scraper_manager.py
│   └── sources/
│       ├── base.py
│       ├── justjoinit.py
│       ├── nofluffjobs.py
│       └── theprotocolit.py
├── utils/                 # Utilities and database handler
│   ├── db_handler.py
│   └── logging_config.py
├── config/                # Configuration settings
├── logs/                  # Application logs
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Container orchestration
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## 🧪 Development Workflow

1. Edit Python files in the repository.
2. Save the file.
3. Docker-mounted source should reload Streamlit automatically.
4. If needed, check container logs.

## 📊 Database Management

### Open PostgreSQL shell

```bash
docker-compose exec db psql -U ${POSTGRES_USER:-CHANGE_ME} -d ${POSTGRES_DB:-CHANGE_ME}
```

### Backup database

```bash
docker-compose exec db pg_dump -U ${POSTGRES_USER:-CHANGE_ME} ${POSTGRES_DB:-CHANGE_ME} > backup.sql
```

### Restore database

```bash
docker-compose exec db psql -U ${POSTGRES_USER:-CHANGE_ME} ${POSTGRES_DB:-CHANGE_ME} < backup.sql
```

## 🐛 Troubleshooting

### Port already in use

```bash
docker-compose down
```

### Changes not reflecting

1. Check logs:
   ```bash
   docker-compose logs -f streamlit-app
   ```
2. Restart containers:
   ```bash
   docker-compose down && docker-compose up --build
   ```

### Database connection issues

```bash
docker-compose ps
docker-compose restart db
```

## 📝 License

See [`LICENSE`](LICENSE) for license details.

## 🔗 Technologies

- Streamlit
- PostgreSQL
- Docker
- BeautifulSoup4
- Pandas
- Plotly
- SQLAlchemy
