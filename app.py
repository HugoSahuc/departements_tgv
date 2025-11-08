import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium

# Charger GeoJSON départements (hors Corse)
with open("departement.geojson", encoding="utf8") as f:
    geojson = json.load(f)
geojson["features"] = [feat for feat in geojson["features"] if feat["properties"]["code"] not in ("2A", "2B")]

# Charger population
pop_df = pd.read_csv("donnees_departements.csv", sep=";")
pop_df["DEP"] = pop_df["DEP"].astype(str)

# Charger JSON simplifié TGV
with open("tgv_desserte.json", encoding="utf8") as f:
    tgv_data = json.load(f)
tgv_df = pd.DataFrame(tgv_data)

# charger lignes lgv
with open("lignes_lgv.geojson", encoding="utf8") as f:
    lgv_geojson = json.load(f)

# Fusionner population et données TGV
df = pop_df.merge(tgv_df, left_on="DEP", right_on="code", how="left")
df['ligne_grande_vitesse'] = df['ligne_grande_vitesse'].astype('boolean').fillna(False)
df['desserte_tgv'] = df['desserte_tgv'].astype('boolean').fillna(False)
df['PTOT'] = pd.to_numeric(df['PTOT'], errors='coerce').fillna(0)

# Mettre à jour propriétés GeoJSON avec population et infos TGV
tgv_dict = df.set_index("DEP")[["ligne_grande_vitesse", "desserte_tgv", "PTOT"]].to_dict(orient='index')
for feat in geojson["features"]:
    code = feat["properties"]["code"]
    data = tgv_dict.get(code, {"ligne_grande_vitesse": False, "desserte_tgv": False, "PTOT": 0})
    feat["properties"].update(data)
    feat["properties"]["population"] = f"{int(data['PTOT']):,}".replace(",", " ")

def color_status(props):
    if props["ligne_grande_vitesse"] and props["desserte_tgv"]:
        return "blue"
    elif props["desserte_tgv"] and not props["ligne_grande_vitesse"]:
        return "green"
    elif props["ligne_grande_vitesse"] and not props["desserte_tgv"]:
        return "orange"
    return "lightgray"

m = folium.Map(location=[46.5, 2.2], zoom_start=6, tiles="cartodbpositron")

def style_function(feature):
    return {
        'fillColor': color_status(feature['properties']),
        'color': 'black',
        'weight': 0.3,
        'fillOpacity': 0.7,
    }

tooltip = folium.GeoJsonTooltip(
    fields=["nom", "population", "ligne_grande_vitesse", "desserte_tgv"],
    aliases=["Département :", "Population :", "LGV traversante :", "Desserte TGV :"],
    localize=True,
)

folium.GeoJson(
    geojson,
    style_function=style_function,
    tooltip=tooltip
).add_to(m)

# Ajouter couche LGV à la carte Folium avec style (ligne rouge par exemple)
folium.GeoJson(
    lgv_geojson,
    name="Lignes LGV",
    style_function=lambda feature: {
        'color': 'red',
        'weight': 3,
        'opacity': 0.8
    }
).add_to(m)

# Ajouter contrôle des couches (pour activer/désactiver la couche LGV)
folium.LayerControl().add_to(m)

# Calculs pourcentage population
pop_total = df['PTOT'].sum()
pop_lgv = df.loc[df['ligne_grande_vitesse'], 'PTOT'].sum()
pop_desserte = df.loc[df['desserte_tgv'], 'PTOT'].sum()
pop_traverse_sans_desserte = df.loc[(df['ligne_grande_vitesse']) & (~df['desserte_tgv']), 'PTOT'].sum()
pop_aucune = df.loc[(~df['ligne_grande_vitesse']) & (~df['desserte_tgv']), 'PTOT'].sum()

# Affichage Streamlit
st.title("Desserte TGV simplifiée des départements français et population couverte")

st.markdown("""
- Vert : Département avec desserte TGV  
- Orange : Département traversé par LGV sans desserte  
- Gris : Département sans desserte ni LGV
""")

st_folium(m, width=800, height=600)

st.metric("Population totale", f"{pop_total:,}".replace(",", " "))

st.subheader("Pourcentage de population couverte")
st.metric("Avec ligne LGV", f"{pop_lgv / pop_total * 100:.2f} %")
st.metric("Avec desserte TGV", f"{pop_desserte / pop_total * 100:.2f} %")
st.metric("Traversé par LGV sans desserte", f"{pop_traverse_sans_desserte / pop_total * 100:.2f} %")
st.metric("Sans desserte ni LGV", f"{pop_aucune / pop_total * 100:.2f} %")

st.subheader("Détail des départements")
st.dataframe(df[["DEP", "Département", "PTOT", "ligne_grande_vitesse", "desserte_tgv"]].rename(
          columns={"DEP": "Code", "Département": "Nom", "PTOT": "Population", "ligne_grande_vitesse": "LGV", 
                   "desserte_tgv": "Desserte TGV"}).sort_values("Population", ascending=False))
