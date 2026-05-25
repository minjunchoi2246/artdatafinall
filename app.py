from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
REST_STOPS_PATH = DATA_DIR / "rest_stops.csv"
MENUS_PATH = DATA_DIR / "menu_items.csv"
STORES_PATH = DATA_DIR / "stores.csv"
RATINGS_PATH = DATA_DIR / "ratings.csv"

st.set_page_config(
    page_title="Korean Highway Rest Stop Food Dashboard",
    page_icon="🍜",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .small-muted {color: #6b7280; font-size: 0.9rem;}
    .badge {display:inline-block; padding:0.18rem 0.55rem; border-radius:999px; background:#f3f4f6; margin-right:0.35rem; font-size:0.8rem;}
    .focus-badge {background:#fff7ed; color:#9a3412; border:1px solid #fed7aa;}
    .signature-card {border:1px solid #e5e7eb; border-radius:18px; padding:1rem; background:white; box-shadow:0 1px 8px rgba(0,0,0,0.04); margin-bottom:0.6rem;}
    .metric-card {border:1px solid #e5e7eb; border-radius:16px; padding:0.9rem 1rem; background:#ffffff;}
    .metric-label {color:#6b7280; font-size:0.82rem;}
    .metric-value {font-weight:700; font-size:1.28rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rest_stops = pd.read_csv(REST_STOPS_PATH)
    menus = pd.read_csv(MENUS_PATH)
    stores = pd.read_csv(STORES_PATH)
    if RATINGS_PATH.exists():
        ratings = pd.read_csv(RATINGS_PATH)
    else:
        ratings = pd.DataFrame(columns=["timestamp", "rest_stop_id", "user_rating", "comment"])

    for col in ["is_focus"]:
        if col in rest_stops.columns:
            rest_stops[col] = rest_stops[col].astype(str).str.lower().isin(["true", "1", "yes"])
    for col in ["is_signature", "is_representative"]:
        if col in menus.columns:
            menus[col] = menus[col].astype(str).str.lower().isin(["true", "1", "yes"])
    if "is_24h" in stores.columns:
        stores["is_24h"] = stores["is_24h"].astype(str).str.lower().isin(["true", "1", "yes"])

    return rest_stops, menus, stores, ratings


def safe_int(value) -> int:
    try:
        return int(float(value))
    except Exception:
        return 0


def parse_time_to_minutes(value: str) -> int | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value == "24:00":
        return 24 * 60
    try:
        hour, minute = value.split(":")[:2]
        return int(hour) * 60 + int(minute)
    except Exception:
        return None


def is_open_now(hours: str, now: datetime | None = None) -> bool:
    """Parse strings like 00:00-24:00 or 08:00-22:00."""
    if not isinstance(hours, str) or "-" not in hours:
        return False
    now = now or datetime.now()
    current = now.hour * 60 + now.minute
    start_s, end_s = [v.strip() for v in hours.split("-", 1)]
    start = parse_time_to_minutes(start_s)
    end = parse_time_to_minutes(end_s)
    if start is None or end is None:
        return False
    if start == 0 and end == 24 * 60:
        return True
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def nearest_rest_stop(lat: float, lon: float, df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    distances = ((df["lat"] - lat) ** 2 + (df["lon"] - lon) ** 2) ** 0.5
    idx = distances.idxmin()
    return str(df.loc[idx, "rest_stop_id"])


def format_krw(value) -> str:
    return f"₩{safe_int(value):,}"


def make_popup_html(row: pd.Series, menus: pd.DataFrame, stores: pd.DataFrame) -> str:
    rest_id = row["rest_stop_id"]
    top_menus = menus[menus["rest_stop_id"] == rest_id].sort_values(
        ["is_signature", "is_representative", "price_krw"], ascending=[False, False, False]
    ).head(4)
    store_types = stores[stores["rest_stop_id"] == rest_id]["store_type"].dropna().unique().tolist()
    menu_html = "".join(
        f"<li>{m.menu_name} · {format_krw(m.price_krw)}</li>" for m in top_menus.itertuples()
    )
    type_text = ", ".join(store_types[:4]) if store_types else "No store data"
    focus = "Top traffic focus" if row.get("is_focus", False) else "Additional rest stop"
    return f"""
    <div style='width:280px; font-family:Arial, sans-serif;'>
      <h4 style='margin:0 0 6px 0;'>{row['display_name']}</h4>
      <div><b>Route:</b> {row['highway_route']} · {row['direction']}</div>
      <div><b>Phone:</b> {row['phone']}</div>
      <div><b>Hours:</b> {row['main_operating_hours']}</div>
      <div><b>Store types:</b> {type_text}</div>
      <div><b>Mode:</b> {focus}</div>
      <hr style='margin:8px 0;'>
      <b>Recommended menus</b>
      <ul style='margin:6px 0 0 16px; padding:0;'>{menu_html}</ul>
    </div>
    """


def build_map(rest_df: pd.DataFrame, menus: pd.DataFrame, stores: pd.DataFrame) -> folium.Map:
    if rest_df.empty:
        center = [36.5, 127.8]
    else:
        center = [rest_df["lat"].mean(), rest_df["lon"].mean()]
    fmap = folium.Map(location=center, zoom_start=7, tiles="CartoDB positron", control_scale=True)

    for _, row in rest_df.iterrows():
        is_focus = bool(row.get("is_focus", False))
        radius = 10 if is_focus else 7
        color = "red" if is_focus else "blue"
        popup = folium.Popup(make_popup_html(row, menus, stores), max_width=330)
        tooltip = f"{row['display_name']} · {row['highway_route']}"
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            popup=popup,
            tooltip=tooltip,
        ).add_to(fmap)
    return fmap


def save_rating(rest_stop_id: str, rating: int, comment: str) -> None:
    RATINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "rest_stop_id": rest_stop_id,
                "user_rating": rating,
                "comment": comment,
            }
        ]
    )
    if RATINGS_PATH.exists():
        existing = pd.read_csv(RATINGS_PATH)
        updated = pd.concat([existing, new_row], ignore_index=True)
    else:
        updated = new_row
    updated.to_csv(RATINGS_PATH, index=False)
    st.cache_data.clear()


def show_metric_card(label: str, value: str, caption: str | None = None) -> None:
    caption_html = f"<div class='small-muted'>{caption}</div>" if caption else ""
    st.markdown(
        f"""
        <div class='metric-card'>
          <div class='metric-label'>{label}</div>
          <div class='metric-value'>{value}</div>
          {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_signature_cards(selected_menus: pd.DataFrame) -> None:
    signatures = selected_menus[selected_menus["is_signature"]].sort_values("price_krw", ascending=False)
    if signatures.empty:
        st.info("No signature food has been marked for this rest stop yet.")
        return
    for menu in signatures.itertuples():
        st.markdown(
            f"""
            <div class='signature-card'>
              <span class='badge focus-badge'>Signature</span>
              <span class='badge'>{menu.category}</span>
              <h4 style='margin:0.5rem 0 0.2rem 0;'>{menu.menu_name}</h4>
              <div class='small-muted'>{menu.store_name} · {menu.available_hours}</div>
              <p style='margin:0.55rem 0;'>{menu.description}</p>
              <b>{format_krw(menu.price_krw)}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_detail(
    selected_id: str,
    rest_stops: pd.DataFrame,
    menus: pd.DataFrame,
    stores: pd.DataFrame,
    ratings: pd.DataFrame,
) -> None:
    selected = rest_stops[rest_stops["rest_stop_id"] == selected_id].iloc[0]
    selected_menus = menus[menus["rest_stop_id"] == selected_id].copy()
    selected_stores = stores[stores["rest_stop_id"] == selected_id].copy()
    selected_ratings = ratings[ratings["rest_stop_id"] == selected_id].copy() if not ratings.empty else ratings

    st.subheader(f"📍 {selected['display_name']}")
    focus_label = "Top-traffic focus rest stop" if selected["is_focus"] else "Additional rest stop"
    open_label = "Open now" if is_open_now(selected["main_operating_hours"]) else "Check hours"
    st.markdown(
        f"<span class='badge focus-badge'>{focus_label}</span><span class='badge'>{selected['highway_route']}</span><span class='badge'>{open_label}</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "The bundled dataset is a runnable seed dataset. Replace it with official API/CSV data for production accuracy."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        show_metric_card("Phone", str(selected["phone"]), selected["direction"])
    with c2:
        show_metric_card("Operating hours", str(selected["main_operating_hours"]), "Main food area")
    with c3:
        avg_price = selected_menus["price_krw"].mean() if not selected_menus.empty else 0
        show_metric_card("Avg. menu price", format_krw(avg_price), "Current selected data")
    with c4:
        if not selected_ratings.empty and selected_ratings["user_rating"].notna().any():
            avg_rating = selected_ratings["user_rating"].astype(float).mean()
            rating_text = f"⭐ {avg_rating:.1f}"
            rating_caption = f"{len(selected_ratings)} local app rating(s)"
        else:
            rating_text = f"⭐ {selected['overall_rating']:.1f}"
            rating_caption = "Seed/base rating"
        show_metric_card("Rating", rating_text, rating_caption)

    detail_tab, menu_tab, store_tab, rating_tab = st.tabs(
        ["Signature", "Menus & Prices", "Stores & Hours", "Rate"]
    )

    with detail_tab:
        st.markdown(f"**Concept:** {selected['signature_summary']}")
        show_signature_cards(selected_menus)

    with menu_tab:
        if selected_menus.empty:
            st.warning("No menu data available for this rest stop.")
        else:
            selected_menus["price"] = selected_menus["price_krw"].apply(format_krw)
            table_cols = [
                "store_name",
                "menu_name",
                "category",
                "price",
                "is_signature",
                "is_representative",
                "available_hours",
                "description",
            ]
            st.dataframe(
                selected_menus[table_cols],
                use_container_width=True,
                hide_index=True,
            )

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                category_counts = selected_menus.groupby("category", as_index=False).size()
                fig = px.pie(
                    category_counts,
                    names="category",
                    values="size",
                    title="Menu category mix",
                    hole=0.42,
                )
                st.plotly_chart(fig, use_container_width=True)
            with chart_col2:
                price_df = selected_menus.sort_values("price_krw", ascending=True)
                fig = px.bar(
                    price_df,
                    x="price_krw",
                    y="menu_name",
                    color="category",
                    orientation="h",
                    title="Menu price comparison",
                    labels={"price_krw": "Price (KRW)", "menu_name": "Menu"},
                )
                st.plotly_chart(fig, use_container_width=True)

    with store_tab:
        if selected_stores.empty:
            st.warning("No store data available for this rest stop.")
        else:
            st.dataframe(
                selected_stores[
                    [
                        "store_name",
                        "store_type",
                        "brand_name",
                        "opening_time",
                        "closing_time",
                        "is_24h",
                        "description",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
            type_counts = selected_stores.groupby("store_type", as_index=False).size()
            fig = px.bar(
                type_counts,
                x="store_type",
                y="size",
                title="Restaurant / store types in this rest stop",
                labels={"store_type": "Store type", "size": "Count"},
            )
            st.plotly_chart(fig, use_container_width=True)

    with rating_tab:
        st.markdown("### Leave a quick rating")
        st.caption("For a public deployment, connect this to a database such as Supabase, Firebase, or Google Sheets.")
        rating = st.slider("Your rating", min_value=1, max_value=5, value=4, step=1)
        comment = st.text_input("Optional comment", placeholder="e.g. Good late-night food, but crowded.")
        if st.button("Save rating", type="primary"):
            save_rating(selected_id, rating, comment)
            st.success("Rating saved locally for this Streamlit session/repository runtime.")
            st.rerun()

        if not selected_ratings.empty:
            st.markdown("### Recent local ratings")
            st.dataframe(selected_ratings.tail(10).sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)


def render_dashboard() -> None:
    rest_stops, menus, stores, ratings = load_data()

    st.title("🍜 Korean Highway Rest Stop Food Dashboard")
    st.caption(
        "Map-first Streamlit dashboard for rest stop restaurants, menus, prices, operating hours, and user ratings."
    )

    with st.sidebar:
        st.header("Controls")
        view_mode = st.radio(
            "Dashboard scope",
            ["Top-traffic focus", "All rest stops"],
            help="Top-traffic focus uses the high-priority rest stops in the seed dataset. Replace traffic values with the official CSV for real ranking.",
        )

        route_options = sorted(rest_stops["highway_route"].dropna().unique().tolist())
        selected_routes = st.multiselect("Highway route", route_options, default=route_options)

        category_options = sorted(menus["category"].dropna().unique().tolist())
        selected_categories = st.multiselect("Food category", category_options, default=category_options)

        only_open_now = st.toggle("Show rest stops open now", value=False)
        show_signature_only = st.toggle("Signature menus only", value=False)

        st.markdown("---")
        st.markdown("**Data mode**")
        st.caption("Bundled seed data now. Replace CSV files in `/data` or connect official APIs later.")

    filtered = rest_stops.copy()
    if view_mode == "Top-traffic focus":
        filtered = filtered[filtered["is_focus"]]
    if selected_routes:
        filtered = filtered[filtered["highway_route"].isin(selected_routes)]
    if only_open_now:
        filtered = filtered[filtered["main_operating_hours"].apply(is_open_now)]

    menu_filtered = menus[menus["category"].isin(selected_categories)].copy() if selected_categories else menus.copy()
    if show_signature_only:
        menu_filtered = menu_filtered[menu_filtered["is_signature"]]
    eligible_ids = menu_filtered["rest_stop_id"].unique().tolist()
    filtered = filtered[filtered["rest_stop_id"].isin(eligible_ids)]

    if filtered.empty:
        st.warning("No rest stops match the current filters. Try changing the sidebar filters.")
        return

    overview1, overview2, overview3, overview4 = st.columns(4)
    with overview1:
        show_metric_card("Visible rest stops", f"{len(filtered):,}", view_mode)
    with overview2:
        show_metric_card("Menu items", f"{len(menu_filtered[menu_filtered['rest_stop_id'].isin(filtered['rest_stop_id'])]):,}", "After filters")
    with overview3:
        avg_price = menu_filtered[menu_filtered["rest_stop_id"].isin(filtered["rest_stop_id"])]["price_krw"].mean()
        show_metric_card("Average price", format_krw(avg_price), "Visible menus")
    with overview4:
        sig_count = menu_filtered[(menu_filtered["rest_stop_id"].isin(filtered["rest_stop_id"])) & (menu_filtered["is_signature"])].shape[0]
        show_metric_card("Signature foods", f"{sig_count:,}", "Separate from general menus")

    map_col, detail_col = st.columns([1.18, 1.0], gap="large")

    with map_col:
        st.subheader("🗺️ Click a rest stop on the map")
        fmap = build_map(filtered, menu_filtered, stores)
        map_data = st_folium(fmap, height=560, use_container_width=True, returned_objects=["last_object_clicked"])

        clicked_id = None
        if map_data and map_data.get("last_object_clicked"):
            clicked = map_data["last_object_clicked"]
            clicked_id = nearest_rest_stop(clicked["lat"], clicked["lng"], filtered)

        st.markdown(
            "<span class='badge focus-badge'>Red: top-traffic focus</span><span class='badge'>Blue: additional rest stop</span>",
            unsafe_allow_html=True,
        )

    with detail_col:
        st.subheader("Selected rest stop")
        default_id = clicked_id or filtered.sort_values("traffic_2024_daily", ascending=False).iloc[0]["rest_stop_id"]
        display_to_id = dict(zip(filtered["display_name"], filtered["rest_stop_id"]))
        id_to_display = {v: k for k, v in display_to_id.items()}
        selected_display = st.selectbox(
            "Select manually or click a map marker",
            options=list(display_to_id.keys()),
            index=list(display_to_id.keys()).index(id_to_display[default_id]) if default_id in id_to_display else 0,
        )
        selected_id = display_to_id[selected_display]
        render_detail(selected_id, rest_stops, menus, stores, ratings)

    st.markdown("---")
    analytics_tab, data_tab, source_tab = st.tabs(["Traffic & food analytics", "All data", "Source notes"])

    with analytics_tab:
        left, right = st.columns(2)
        with left:
            traffic_df = filtered.sort_values("traffic_2024_daily", ascending=True)
            fig = px.bar(
                traffic_df,
                x="traffic_2024_daily",
                y="display_name",
                color="highway_route",
                orientation="h",
                title="Priority by daily traffic value in current dataset",
                labels={"traffic_2024_daily": "Daily traffic value", "display_name": "Rest stop"},
            )
            st.plotly_chart(fig, use_container_width=True)
        with right:
            visible_menus = menu_filtered[menu_filtered["rest_stop_id"].isin(filtered["rest_stop_id"])]
            avg_by_route = visible_menus.merge(rest_stops[["rest_stop_id", "highway_route"]], on="rest_stop_id")
            avg_by_route = avg_by_route.groupby(["highway_route", "category"], as_index=False)["price_krw"].mean()
            fig = px.bar(
                avg_by_route,
                x="highway_route",
                y="price_krw",
                color="category",
                barmode="group",
                title="Average menu price by route and category",
                labels={"price_krw": "Average price (KRW)", "highway_route": "Route"},
            )
            st.plotly_chart(fig, use_container_width=True)

    with data_tab:
        st.markdown("### Rest stops")
        st.dataframe(filtered.sort_values("traffic_2024_daily", ascending=False), use_container_width=True, hide_index=True)
        st.markdown("### Menus")
        st.dataframe(menu_filtered[menu_filtered["rest_stop_id"].isin(filtered["rest_stop_id"])], use_container_width=True, hide_index=True)
        st.markdown("### Stores")
        st.dataframe(stores[stores["rest_stop_id"].isin(filtered["rest_stop_id"])], use_container_width=True, hide_index=True)

    with source_tab:
        st.markdown(
            """
            ### How to replace the seed data with official data
            1. Download or call the official public datasets.
            2. Normalize rest stop names with direction, e.g. `안성휴게소(부산방향)`.
            3. Replace these files:
               - `data/rest_stops.csv`
               - `data/menu_items.csv`
               - `data/stores.csv`
            4. Keep `rest_stop_id` consistent across all tables.

            ### Recommended official sources
            - Korea Expressway Corporation rest stop users / traffic CSV
            - Korea Expressway Corporation route & direction rest stop facility API
            - Korea Expressway Corporation rest stop food menu API
            - Korea Expressway Corporation monthly top-selling store/menu data

            ### Important note
            The included CSV files are seed data for a working prototype. Phone numbers, exact operating hours, coordinates, menu names, and prices should be replaced with official data before public release.
            """
        )


if __name__ == "__main__":
    render_dashboard()
