# Architecture Decision Record: Krakow Spatial Agent (KSA)

## 1. System Overview
Krakow Spatial Agent to autonomiczny system Geo-AI przeznaczony do translacji zapytań w języku naturalnym na przestrzenny dialekt PostGIS SQL, odpytujący zbiory danych Zarządu Transportu Publicznego w Krakowie (ZTP). Wyniki zapytań są przekształcane do standardu GeoJSON i wizualizowane na interaktywnej mapie webowej.

## 2. Multi-Container Layered Architecture
System opiera się na architekturze modularnej, skonteneryzowanej za pomocą Docker Compose:

               +---------------------------------------------------+
               |             Client / Web Browser                  |
               +---------------------------------------------------+
                                         |
                                         | HTTP / WebSocket
                                         v
               +---------------------------------------------------+
               |          Frontend Service (Streamlit)             |
               |  - Interfejs czatu w języku naturalnym            |
               |  - Wizualizacja przestrzenna (PyDeck / Folium)    |
               +---------------------------------------------------+
                                         |
                                         | Wewnętrzne REST API (GeoJSON)
                                         v
               +---------------------------------------------------+
               |           Backend Service (FastAPI)               |
               |  - Asynchroniczna pula sesji (SQLAlchemy/asyncpg) |
               |  - Orkiestracja agenta w LangGraph                |
               |  - Parser AST i guardraile bezpieczeństwa (SELECT)|
               +---------------------------------------------------+
                                         |
                                         | Połączenie asynchroniczne
                                         v
               +---------------------------------------------------+
               |      Spatial Database (PostgreSQL 16 + PostGIS)   |
               |  - Warstwy transportowe ZTP (EPSG:4326 / 2180)    |
               |  - Indeksy przestrzenne GIST                      |
               |  - Trwały wolumen dyskowy (postgis_data)          |
               +---------------------------------------------------+

## 3. Spatial Data Schema (ZTP Krakow Layers)
Dane przestrzenne są przetwarzane w układzie współrzędnych WGS 84 (EPSG:4326) z rzutowaniem metrycznym do obliczeń dystansów (`geography` lub EPSG:2180):

### Schemat tabel:
* **`stops`**: Słupki oraz platformy przystankowe.
  * `id` (Integer, Primary Key)
  * `stop_name` (String, Indexed)
  * `stop_type` (Enum: tram, bus)
  * `has_shelter` (Boolean)
  * `geom` (Geometry: Point, SRID 4326, GIST Index)
* **`bike_racks`**: Stojaki rowerowe oraz stacje naprawcze.
  * `id` (Integer, Primary Key)
  * `capacity` (Integer)
  * `rack_type` (String)
  * `geom` (Geometry: Point, SRID 4326, GIST Index)
* **`sim_boundaries`**: Granice jednostek Krakowskiego Systemu Informacji Miejskiej (SIM).
  * `id` (Integer, Primary Key)
  * `district_name` (String, Indexed)
  * `sim_code` (String)
  * `geom` (Geometry: MultiPolygon, SRID 4326, GIST Index)

## 4. LangGraph Decision Workflow
Silnik Text-to-Spatial-SQL realizuje samokorygujący się graf decyzyjny (Self-Correction Loop):
1. **Schema Context Injection**: Generowanie promptu uzupełnionego o DDL bazy danych oraz przykłady użycia funkcji PostGIS (`ST_DWithin`, `ST_Intersects`, `ST_Buffer`).
2. **SQL Generation Node**: Tłumaczenie intencji użytkownika na zapytanie PostGIS SQL przez model LLM.
3. **Guardrail Node**: Weryfikacja składni AST – dopuszczenie wyłącznie zapytań `SELECT` oraz blokowanie operacji mutujących (`DROP`, `DELETE`, `UPDATE`, `ALTER`).
4. **Execution & Self-Correction**: Uruchomienie zapytania w sesji tylko do odczytu; w przypadku błędu bazy PostgreSQL komunikat błędu trafia z powrotem do LLM w celu poprawy (maksymalnie 2 iteracje).
5. **GeoJSON Serializer**: Konwersja geometrii wynikowych do formatu RFC 7946 GeoJSON.
