import os
from typing import Any

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from vehicle_filter import is_in_krakow

st.set_page_config(page_title="Kraków Transit Explorer", page_icon="🚋", layout="wide")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api/v1")
KRAKOW_COORDS = [50.0614, 19.9383]

st.title("🚋 Kraków Transit Explorer")


@st.cache_data(ttl=300)
def fetch_all_routes() -> list[dict[str, Any]]:
    response = requests.get(f"{BACKEND_URL}/transit/routes", timeout=5)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def fetch_route_geometry(
    route_short_name: str, direction_id: int | None
) -> dict[str, Any]:
    params = {} if direction_id is None else {"direction_id": direction_id}
    response = requests.get(
        f"{BACKEND_URL}/transit/routes/{route_short_name}",
        params=params,
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def fetch_route_stops(route_short_name: str) -> list[dict[str, Any]]:
    response = requests.get(
        f"{BACKEND_URL}/transit/routes/{route_short_name}/stops", timeout=5
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=10)
def fetch_live_vehicles(route_short_name: str | None = None) -> dict[str, Any]:
    params = (
        {"route_short_name": route_short_name} if route_short_name is not None else {}
    )
    response = requests.get(f"{BACKEND_URL}/live/vehicles", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def add_live_vehicle_markers(
    map_object: folium.Map, live_data: dict[str, Any] | None
) -> None:
    if not live_data or "features" not in live_data:
        return

    for feature in live_data["features"]:
        coordinates = feature["geometry"]["coordinates"]
        if not is_in_krakow(coordinates):
            continue

        properties = feature["properties"]
        vehicle_type = properties.get("vehicle_type", "bus")
        folium.Marker(
            location=[coordinates[1], coordinates[0]],
            icon=folium.Icon(
                color="blue" if vehicle_type == "tram" else "orange",
                icon="train" if vehicle_type == "tram" else "bus",
                prefix="fa",
            ),
            popup=f"Linia: {properties.get('route_short_name')}<br>ID: {
                properties.get('vehicle_id')
            }",
        ).add_to(map_object)


with st.sidebar:
    st.header("Wybór linii")
    direction_label = st.radio(
        "Kierunek:",
        options=("Tam", "Powrót", "Oba"),
        horizontal=True,
    )
    direction_ids = {"Tam": 0, "Powrót": 1, "Oba": None}
    selected_direction = direction_ids[direction_label]

    try:
        routes_list = fetch_all_routes()
    except requests.exceptions.RequestException:
        st.error("Nie udało się pobrać listy linii z backendu.")
        routes_list = []
    if routes_list:
        route_options = {
            f"{str(r['route_short_name']).strip()} - {
                r.get('route_long_name', '')
            }": str(r["route_short_name"]).strip()
            for r in routes_list
        }
        all_vehicles_option = "🌍 Wszystkie pojazdy na żywo"
        route_options = {all_vehicles_option: None, **route_options}
        selected_label = st.selectbox(
            "Wybierz linię:",
            options=list(route_options.keys()),
            index=1,
        )
        selected_route = route_options[selected_label]
        show_all_vehicles = selected_label == all_vehicles_option
    else:
        selected_route = st.text_input("Numer linii:", "139").strip()
        show_all_vehicles = False

    show_live = st.checkbox("Pokaż pojazdy na żywo 📡", value=True)
    refresh_live = st.button("Odśwież pozycje 🔄", use_container_width=True)

if refresh_live:
    fetch_live_vehicles.clear()

if selected_route or show_all_vehicles:
    col_map, col_details = st.columns([3, 1])

    with col_map:
        with st.spinner("Pobieranie trasy i przystanków..."):
            try:
                r_geojson = (
                    fetch_route_geometry(selected_route, selected_direction)
                    if selected_route and not show_all_vehicles
                    else None
                )
                r_stops = (
                    fetch_route_stops(selected_route)
                    if selected_route and not show_all_vehicles
                    else []
                )
            except requests.exceptions.RequestException:
                st.error("Błąd połączenia z backendem")
                st.stop()

    live_data = None
    if show_live:
        with col_map:
            with st.spinner("Pobieranie pojazdów na żywo..."):
                try:
                    live_data = fetch_live_vehicles(
                        None if show_all_vehicles else selected_route
                    )
                except requests.exceptions.RequestException:
                    st.error("Nie udało się pobrać pozycji pojazdów na żywo.")

    m = folium.Map(location=KRAKOW_COORDS, zoom_start=12, tiles="OpenStreetMap")

    if r_geojson and "type" in r_geojson:
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

    bounds = m.get_bounds()
    if bounds != [[None, None], [None, None]]:
        m.fit_bounds(bounds)

    add_live_vehicle_markers(m, live_data)

    with col_map:
        st_folium(
            m,
            width="100%",
            height=700,
            key="transit-map",
            returned_objects=[],
        )

    if selected_route and not show_all_vehicles:
        with col_details:
            st.subheader(f"Linia {selected_route}")
            if isinstance(r_stops, list):
                for stop in r_stops:
                    st.write(f"**{stop['stop_sequence']}.** {stop['stop_name']}")
    else:
        col_details.empty()
