# Code Revive - Web Interface

A beautiful and modern web interface for the Code Revive backend that integrates older repositories with latest codebases.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web Server

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`

### 3. Access the Interface

Open your browser and navigate to:
- **Local:** `http://localhost:5000`
- **Network:** `http://YOUR_IP:5000`

## 📖 How to Use

1. **Enter Repository URLs:**
   - **R_base**: The modern/latest repository you want to integrate code into
   - **R_old**: The older repository that needs to be integrated

2. **Submit the Job:**
   - Click "Start Integration Process"
   - You'll be redirected to a status page

3. **Monitor Progress:**
   - The status page auto-refreshes every 3 seconds
   - Watch the progress through different stages:
     - Initializing agent
     - Setting up R_base environment
     - Setting up R_old environment
     - Resolving dependencies
     - Final verification

4. **View Results:**
   - When complete, you'll see the work directory where results are stored
   - Check the status badge for success or failure

## 🎨 Features

- **Modern UI:** Beautiful gradient design with smooth animations
- **Real-time Updates:** Auto-refreshing status page
- **Progress Tracking:** Visual progress bar and detailed step information
- **Error Handling:** Clear error messages if something goes wrong
- **Responsive Design:** Works on desktop and mobile devices
- **Job Management:** Each integration gets a unique job ID

## 🏗️ Architecture

```
rebibemecode/
├── app.py                  # Flask web application
├── main.py                 # Original CLI interface
├── templates/
│   ├── index.html         # Main form page
│   └── results.html       # Status/results page
├── classes/
│   ├── revive_agent.py
│   └── utils.py
└── work_dir/              # Generated during jobs
```

## 🔗 API Endpoints

### `GET /`
Home page with the form to submit new integration jobs.

### `POST /submit`
Submit a new integration job.

**Request Body:**
```json
{
  "r_base": "https://github.com/user/base-repo",
  "r_old": "https://github.com/user/old-repo"
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "message": "Job submitted successfully"
}
```

### `GET /status/<job_id>`
Get the current status of a job.

**Response:**
```json
{
  "status": "running",
  "current_step": "Resolving dependencies",
  "r_base": "https://...",
  "r_old": "https://...",
  "work_directory": "./work_dir/invocation_...",
  "started_at": "2025-10-12T..."
}
```

### `GET /results/<job_id>`
View the results page for a specific job (HTML page).

## 🔧 Configuration

You can modify these settings in `app.py`:

- **Port:** Change the port in the last line: `app.run(port=5000)`
- **Debug Mode:** Set `debug=False` for production
- **Timeout:** Adjust the `timeout` parameter in ReviveAgent calls
- **Auto-refresh Rate:** Modify the interval in `results.html` (default: 3 seconds)

## 📝 Notes

- Job statuses are stored in memory. For production, consider using Redis or a database.
- Long-running jobs may timeout depending on your web server configuration.
- The work directory grows with each job; consider implementing cleanup logic.
- Make sure Cursor CLI is installed: `curl https://cursor.com/install -fsS | bash`

## 🐛 Troubleshooting

**Issue:** "Cursor CLI not found"
- **Solution:** Install Cursor CLI using the command in the error message

**Issue:** Jobs stuck in "running" status
- **Solution:** Check the console output of `app.py` for error messages

**Issue:** Cannot connect to the web interface
- **Solution:** Make sure the port 5000 is not blocked by firewall

## 💡 Tips

- Use the default example repositories to test the system
- Keep the terminal open to see real-time logs
- Each job creates a timestamped directory in `work_dir/`
- You can run multiple jobs, but they'll execute sequentially based on agent availability

## 🚀 Production Deployment

For production deployment, consider:

1. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. Set up a reverse proxy with Nginx

3. Use a proper database for job storage

4. Implement authentication if needed

5. Set up proper logging and monitoring

6. Consider using Celery for background job processing


