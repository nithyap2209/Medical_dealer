# Medical Dealer Scraper - All India

Automated web scraping tool to collect **medical dealers, pharmaceutical distributors, and healthcare suppliers** contact information across all **28 states and 8 union territories (783 districts)** of India.

## Data Sources

| Source | Method | Speed |
|--------|--------|-------|
| **Google Maps** | Playwright browser automation | Slow (anti-detection delays) |
| **JustDial** | Scrapy spider (HTML/API parsing) | Fast |
| **IndiaMART** | Scrapy spider (__NEXT_DATA__ JSON) | Fast |

## Data Collected

- Business Name
- Phone Number(s)
- Address
- District & State
- City & Pincode (JustDial/IndiaMART)
- Business Category
- Source URL

## Features

- **Resume support** — progress saved to JSON, restarts from where it stopped
- **Smart filtering** — only collects medical/pharma related businesses using keyword matching
- **Phone validation** — skips entries without valid 10+ digit phone numbers
- **Duplicate removal** — filters by name+district and phone number
- **Anti-detection** — browser rotation, random delays, stealth mode (Google Maps)
- **Auto Excel generation** — state-wise formatted Excel files with headers, filters, and styling

## Usage

```bash
# Google Maps scraper (all states, Tamil Nadu first)
python scraper.py

# JustDial + IndiaMART via Scrapy
python run.py                            # All states, all spiders
python run.py --spider justdial          # JustDial only
python run.py --spider indiamart         # IndiaMART only
python run.py --state "Tamil Nadu"       # Single state
python run.py --excel-only               # Generate Excel from existing data
```

## Output

- `output/` — Google Maps Excel files (state-wise)
- `output_justdial/` — JustDial Excel files (state-wise + combined)
- `scrape_progress.json` — Google Maps progress tracker
- `output/scraped_data.json` — JustDial/IndiaMART raw data

## Tech Stack

- **Python 3**
- **Playwright** — headless browser automation for Google Maps
- **Scrapy** — web scraping framework for JustDial & IndiaMART
- **openpyxl** — Excel file generation with formatting

## Requirements

```bash
pip install playwright scrapy openpyxl
playwright install chromium
```
