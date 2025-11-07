import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium

# Charger le GeoJSON et retirer Corse
with open("departement.geojson", encoding="utf8") as f:
    geojson = json.load(f)

features = [feat for feat in geojson["features"] if feat["properties"]["code"] not in ("2A", "2B")]
geojson["features"] = features

# Charger la population
data = pd.read_csv("donnees_departements.csv", sep=";")
data = data.astype({'DEP': str})

# Clé code départ → population
pop_dict = data.set_index('DEP')['PTOT'].to_dict()

# Ajouter la population dans les propriétés du GeoJSON pour le tooltip
for feat in geojson["features"]:
    code = feat["properties"]["code"]
    pop = pop_dict.get(code, "N/A")
    feat["properties"]["population"] = f"{pop:,}".replace(",", " ") if pop != "N/A" else "N/A"

# Créer la carte
m = folium.Map(location=[46.5, 2.2], zoom_start=6, tiles="cartodbpositron")

# Choroplèthe
folium.Choropleth(
    geo_data=geojson,
    data=data,
    columns=["DEP", "PTOT"],
    key_on="feature.properties.code",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Population totale (2025)",
    nan_fill_color="white"
).add_to(m)

# Tooltip avec nom et population
tooltip = folium.GeoJsonTooltip(
    fields=["nom", "population"],
    aliases=["Département :", "Population :"],
    localize=True,
    sticky=False,
    labels=True,
    style="""
        background-color: #F0EFEF;
        border: 1px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """,
    max_width=250,
)

folium.GeoJson(
    geojson,
    style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 0.2},
    tooltip=tooltip,
).add_to(m)

# Affichage Streamlit
st.title("Population des départements de France métropolitaine (hors Corse)")
st.markdown("Survolez un département pour voir sa population.")
st_folium(m, width=800, height=600)

# Afficher tableau population
st.dataframe(data[["DEP", "Département", "PTOT"]].rename(columns={"DEP": "Code", "Département": "Nom", "PTOT": "Population"}).sort_values("Population", ascending=False))
st.metric("Population totale affichée", f"{data['PTOT'].sum():,}".replace(",", " "))
