# Radar Mikro-nisz - IT Job Market Analysis

Multi-page Streamlit application for analyzing IT job market niches vs mainstream opportunities.

## 🚀 Quick Start (Windows)

### Prerequisites
- Docker Desktop installed and running
- Git

### Setup & Run

1. **Clone the repository:**

2. **Copy environment file:**
   ```powershell
   copy .env.example .env
   ```

3. **Start development environment:**
   ```powershell
   .\manage.ps1 dev
   ```

4. **Access the application:**
   - Open browser: http://localhost:8501
   - Changes to `.py` files will auto-reload! ✨

## 🛠️ Development Commands

Use the PowerShell script for all operations:

```powershell
# Start development with hot reload
.\manage.ps1 dev

# View logs
.\manage.ps1 logs

# Access container shell
.\manage.ps1 shell

# Access PostgreSQL database
.\manage.ps1 db-shell

# Stop containers
.\manage.ps1 stop

# Rebuild from scratch
.\manage.ps1 rebuild

# Clean everything
.\manage.ps1 clean

# Show all commands
.\manage.ps1 help
```

### Alternative: VS Code Tasks

Press `Ctrl+Shift+P` → "Tasks: Run Task" → Select:
- **Start Dev Environment** - Launch with hot reload
- **View Logs** - Monitor application logs
- **Stop Dev Environment** - Stop containers
- **Rebuild Containers** - Full rebuild

### Alternative: Direct Docker Commands

```powershell
# Start development
docker-compose -f docker-compose.dev.yml up

# Stop
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f streamlit-app
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
├── Dockerfile             # Production Docker image
├── docker-compose.yml     # Production setup
├── docker-compose.dev.yml # Development setup (hot reload)
└── manage.ps1             # Windows management script
```

## 🧪 Development Workflow

1. **Edit any Python file** in VS Code
2. **Save the file** - Streamlit auto-reloads
3. **Refresh browser** to see changes
4. **Check logs** if needed: `.\manage.ps1 logs`

**No Python installation needed locally!** Everything runs in Docker.

## 🔄 Updating Dependencies

1. Edit `requirements.txt`
2. Rebuild: `.\manage.ps1 rebuild`

## 📊 Database Management

### Access PostgreSQL
```powershell
.\manage.ps1 db-shell
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
# Stop containers
.\manage.ps1 stop

# Or kill process on port 8501
Get-Process -Id (Get-NetTCPConnection -LocalPort 8501).OwningProcess | Stop-Process
```

### Changes Not Reflecting
1. Check logs: `.\manage.ps1 logs`
2. Hard refresh browser: `Ctrl+Shift+R`
3. Rebuild if needed: `.\manage.ps1 rebuild`

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