import os

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Kraków Transit Explorer", page_icon="🚋", layout="wide")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
KRAKOW_COORDS = [50.0614, 19.9383]

st.title("🚋 Kraków Transit Explorer")


@st.cache_data(ttl=300)
def fetch_all_routes():
    try:
        resp = requests.get(f"{BACKEND_URL}/transit/routes", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass
    return []


routes_list = fetch_all_routes()

with st.sidebar:
    st.header("Wybór linii")
    if routes_list:
        route_options = {
            f"{str(r['route_short_name']).strip()} - {
                r.get('route_long_name', '')
            }": str(r["route_short_name"]).strip()
            for r in routes_list
        }
        selected_label = st.selectbox(
            "Wybierz linię:",
            options=list(route_options.keys()),
            index=0,
        )
        selected_route = route_options[selected_label]
    else:
        selected_route = st.text_input("Numer linii:", "139").strip()

    show_live = st.checkbox("Pokaż pojazdy na żywo 📡", value=True)
    st.button("Odśwież pozycje 🔄", use_container_width=True)

if selected_route:
    col_map, col_details = st.columns([3, 1])
    with st.spinner("Pobieranie danych..."):
        try:
            r_geojson = requests.get(
                f"{BACKEND_URL}/transit/routes/{selected_route}"
            ).json()
            r_stops = requests.get(
                f"{BACKEND_URL}/transit/routes/{selected_route}/stops"
            ).json()
            r_live = (
                requests.get(
                    f"{BACKEND_URL}/live/vehicles?route_short_name={selected_route}"
                ).json()
                if show_live
                else None
            )
        except requests.exceptions.RequestException:
            st.error("Błąd połączenia z backendem")
            st.stop()

    m = folium.Map(location=KRAKOW_COORDS, zoom_start=12, tiles="OpenStreetMap")

    if "type" in r_geojson:
        folium.GeoJson(
            r_geojson, style_function=lambda _: {"color": "#d90429", "weight": 5}
        ).add_to(m)

    for stop in r_stops if isinstance(r_stops, list) else []:
        folium.CircleMarker(
            location=[stop.get("lat"), stop.get("lon")],
            radius=5,
            color="#2b2d42",
            fill=True,
            popup=f"#{stop['stop_sequence']} {stop['stop_name']}",
        ).add_to(m)

    if show_live and r_live and "features" in r_live:
        for feat in r_live["features"]:
            coords = feat["geometry"]["coordinates"]
            props = feat["properties"]
            v_type = props.get("vehicle_type", "bus")
            folium.Marker(
                location=[coords[1], coords[0]],
                icon=folium.Icon(
                    color="blue" if v_type == "tram" else "orange",
                    icon="train" if v_type == "tram" else "bus",
                    prefix="fa",
                ),
                popup=f"Linia: {props.get('route_short_name')}<br>ID: {
                    props.get('vehicle_id')
                }",
            ).add_to(m)

    m.fit_bounds(m.get_bounds())

    with col_map:
        st_folium(m, width="100%", height=700)

    with col_details:
        st.subheader(f"Linia {selected_route}")
        if isinstance(r_stops, list):
            for stp in r_stops:
                st.write(f"**{stp['stop_sequence']}.** {stp['stop_name']}")
