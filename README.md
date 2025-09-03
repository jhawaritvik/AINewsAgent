AINewsAgent is an automated AI news aggregator and summarizer designed to keep you updated with the latest developments. It pulls news from various sources, including RSS feeds and Reddit, and compiles them into a digestible summary or a detailed report. The final report is delivered to your email inbox, making it a seamless and hands-off way to consume your daily dose of AI news.
---


Key Features
- **News Aggregation:** Gathers headlines and articles from configurable RSS feeds and Reddit subreddits.
- **Intelligent Summarization:** Clusters and summarizes news items to create a concise digest or a full HTML/Markdown report.
- **Email Delivery:** Sends the generated report to a specified email address using SMTP.
- **Automation-Ready:** Easily set up for daily execution using Windows Task Scheduler or GitHub Actions.
- **Extensible Architecture:** Includes placeholders for future integrations with platforms like Twitter/X and Discord.
- **Image Support:** Embeds inline images from source articles when available.

---

<!--- End of Features section --->

Setup Instructions
1. **Create and Activate a Python Virtual Environment:**  
   Set up a new environment to manage dependencies.
   ```
   python -m venv .venv
   source .venv/bin/activate      # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies:**  
   Use pip to install the required packages.
   ```
   pip install -r requirements.txt
   ```

3. **Configure Your Settings:**  
   Copy the example configuration file and update it with your personal settings.
   ```
   cp config.example.yaml config.yaml    # On Windows: copy config.example.yaml config.yaml
   ```
   Open the `config.yaml` file and provide your SMTP email credentials, news sources (RSS feed URLs, subreddit names), and other report preferences.

4. **Run a Test:**  
   Execute the script once to confirm everything is working correctly.
   ```
   python -m src.cli --once
   ```
   This command fetches news, generates a report, and sends it to your configured email address.

---

<!--- End of Quick Start section --->

Scheduling & Automation
Automating AINewsAgent to run daily ensures you receive a fresh report without any manual intervention.

Option 1: Windows Task Scheduler
- Create a new task with the following properties:
  - **Program/script:** `python`
  - **Add arguments:** `-m src.cli --once`
  - **Start in:** The full file path to your AINewsAgent directory
  - **Trigger:** Set a daily trigger at your preferred time

Option 2: GitHub Actions
Create a file named .github/workflows/daily.yml and add the following content. You'll need to store your email username, password, and receiver email as GitHub Actions secrets in your repository settings.

- YAML

name: Daily News Digest

on:
  schedule:
    - cron: '30 8 * * *' # Runs every day at 8:30 AM UTC, which is 1 PM IST

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Generate config file
        env:
          EMAIL_USER: ${{ secrets.EMAIL_USER }}
          EMAIL_PASS: ${{ secrets.EMAIL_PASS }}
          EMAIL_RECEIVER: ${{ secrets.EMAIL_RECEIVER }}
        run: |
          cp config.example.yaml config.yaml
          sed -i 's/sender_email: ""/sender_email: "$EMAIL_USER"/' config.yaml
          sed -i 's/sender_password: ""/sender_password: "$EMAIL_PASS"/' config.yaml
          sed -i 's/receiver_email: ""/receiver_email: "$EMAIL_RECEIVER"/' config.yaml

      - name: Run AINewsAgent
        run: python -m src.cli --report # Change to --digest for a shorter report
