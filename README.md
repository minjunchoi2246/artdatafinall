# Korean Highway Rest Stop Food Dashboard

A Streamlit dashboard for Korean highway rest stop food information.

## Features

- Map-first dashboard using Folium
- Top-traffic focus view
- Additional rest stop view
- Clickable rest stop markers with popup information
- Menu database with prices, categories, and signature foods
- Store type and operating hour table
- Interactive charts
- Local star rating system

## Project Structure

```text
rest_stop_dashboard/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── data/
    ├── rest_stops.csv
    ├── menu_items.csv
    ├── stores.csv
    └── ratings.csv
```

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create a GitHub repository.
2. Upload all files in this folder.
3. Go to Streamlit Community Cloud.
4. Select the repository and set `app.py` as the main file.
5. Deploy.

## Data Notice

The bundled CSV files are a runnable seed dataset for prototyping. Replace them with official data before public release.

Recommended sources:

- Korea Expressway Corporation rest stop users / traffic CSV
- Korea Expressway Corporation route & direction rest stop facility API
- Korea Expressway Corporation rest stop food menu API
- Korea Expressway Corporation monthly top-selling store/menu data

## Rating System Notice

The current rating system saves ratings into `data/ratings.csv`. On Streamlit Cloud, this is not a permanent database. For a public app, connect the rating form to Supabase, Firebase, Google Sheets, or another database.
