# Radar Mikro-nisz - IT Job Market Analysis

Multi-page Streamlit application for analyzing IT job market niches vs mainstream opportunities.

## 🚀 Quick Start (Windows)

### Prerequisites
- Docker Desktop installed and running
- Git

### Setup & Run

1. **Clone the repository**

2. **Copy environment file:**
   ```powershell
   copy .env.example .env
   ```

3. **Start development environment:**
   
   **Option A: VS Code Tasks (Recommended)**
   - Press `Ctrl+Shift+B` or
   - Press `Ctrl+Shift+P` → "Tasks: Run Task" → "Start Dev Environment"

   **Option B: Direct Docker command**
   ```powershell
   docker-compose -f docker-compose.dev.yml up
   ```

4. **Access the application:**
   - Open browser: http://localhost:8501
   - Changes to `.py` files will auto-reload! ✨

## 🛠️ Development Commands

### VS Code Tasks (Recommended)

Press `Ctrl+Shift+P` → "Tasks: Run Task" or `Ctrl+Shift+B` for quick build. Available tasks:

**Development:**
- **Start Dev Environment** (`Ctrl+Shift+B`) - Launch with hot reload
- **Stop Dev Environment** - Stop all containers
- **Full Restart** - Sequential stop and start
- **Rebuild Containers** - Full rebuild with no cache

**Monitoring:**
- **View Logs** - Monitor application logs in real-time

**Testing & Maintenance:**
- **Run Tests** - Execute pytest in container
- **Install Dependencies** - Update packages from requirements.txt
- **Run Scraper** - Execute all scrapers via ScraperManager
- **Database Shell** - Open PostgreSQL interactive shell

### Direct Docker Commands

```powershell
# Start development with hot reload
docker-compose -f docker-compose.dev.yml up

# Stop containers
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f streamlit-app

# Rebuild containers
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up

# Access container shell
docker-compose -f docker-compose.dev.yml exec streamlit-app /bin/bash

# Access PostgreSQL database
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d radar_db

# Run tests
docker-compose -f docker-compose.dev.yml exec streamlit-app pytest tests/ -v

# Install dependencies
docker-compose -f docker-compose.dev.yml exec streamlit-app pip install -r requirements.txt
```

## 📁 Project Structure

```
.
├── app.py                 # Main Streamlit application
├── pages/                 # Streamlit pages
│   ├── 1_Home.py
│   ├── 2_Konkurencja.py
│   ├── 3_Regresja.py
│   ├── 4_Kalkulator_ROI.py
│   └── 5_Metodologia.py
├── scrapers/              # Web scraping modules
│   ├── scraper_manager.py
│   └── sources/
│       ├── base.py
│       ├── justjoinit.py
│       ├── nofluffjobs.py
│       └── theprotocolit.py
├── utils/                 # Utility functions
│   ├── db_handler.py
│   └── logging_config.py
├── config/                # Configuration
├── logs/                  # Application logs
├── .vscode/               # VS Code configuration
│   └── tasks.json         # Automated development tasks
├── Dockerfile             # Production Docker image
├── docker-compose.yml     # Production setup
└── docker-compose.dev.yml # Development setup (hot reload)
```

## 🧪 Development Workflow

1. **Edit any Python file** in VS Code
2. **Save the file** - Streamlit auto-reloads
3. **Refresh browser** to see changes
4. **Check logs** if needed: Use "View Logs" task or `docker-compose -f docker-compose.dev.yml logs -f streamlit-app`

**No Python installation needed locally!** Everything runs in Docker.

## 🔄 Updating Dependencies

1. Edit `requirements.txt`
2. Use "Install Dependencies" task or rebuild containers

## 📊 Database Management

### Access PostgreSQL
Use "Database Shell" task or:
```powershell
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d radar_db
```

### Backup Database
```powershell
docker-compose -f docker-compose.dev.yml exec db pg_dump -U navigator blue_ocean_db > backup.sql
```

### Restore Database
```powershell
Get-Content backup.sql | docker-compose -f docker-compose.dev.yml exec -T db psql -U navigator blue_ocean_db
```

## 🐛 Troubleshooting

### Port Already in Use
```powershell
# Stop containers using VS Code task or:
docker-compose -f docker-compose.dev.yml down

# Or kill process on port 8501
Get-Process -Id (Get-NetTCPConnection -LocalPort 8501).OwningProcess | Stop-Process
```

### Changes Not Reflecting
1. Check logs using "View Logs" task
2. Hard refresh browser: `Ctrl+Shift+R`
3. Rebuild using "Rebuild Containers" task

### Database Connection Issues
```powershell
# Check container status
docker-compose -f docker-compose.dev.yml ps

# Restart database
docker-compose -f docker-compose.dev.yml restart db
```

## 🚢 Production Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for production deployment instructions.

## 📝 License

See [`LICENSE`](LICENSE) file for details.

## 🔗 Technologies

- **Streamlit** - Web application framework
- **Playwright** - Web scraping with browser automation
- **PostgreSQL** - Database
- **Docker** - Containerization
- **BeautifulSoup4** - HTML parsing
- **Pandas** - Data analysis
- **Plotly** - Interactive visualizations