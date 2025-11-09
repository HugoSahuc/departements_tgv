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
pop_df["DEP"] = pop_df["DEP"].astype(str).str.zfill(2)
tgv_df["code"] = tgv_df["code"].astype(str).str.zfill(2)
df = pop_df.merge(tgv_df, left_on="DEP", right_on="code", how="left")
df['ligne_grande_vitesse'] = df['ligne_grande_vitesse'].astype('boolean').fillna(False)
df['desserte_tgv'] = df['desserte_tgv'].astype('boolean').fillna(False)
df['PTOT'] = pd.to_numeric(df['PTOT'], errors='coerce').fillna(0)

# Utilisation de session_state pour stocker les valeurs modifiables
if 'lgv_vals' not in st.session_state or 'desserte_vals' not in st.session_state:
    st.session_state.lgv_vals = df['ligne_grande_vitesse'].tolist()
    st.session_state.desserte_vals = df['desserte_tgv'].tolist()

# Mettre à jour propriétés GeoJSON avec population et infos TGV
def update_geojson_props(df):
    tgv_dict = df.set_index("DEP")[["ligne_grande_vitesse", "desserte_tgv", "PTOT"]].to_dict(orient='index')
    for feat in geojson["features"]:
        code = feat["properties"]["code"]
        data = tgv_dict.get(code, {"ligne_grande_vitesse": False, "desserte_tgv": False, "PTOT": 0})
        feat["properties"].update(data)
        feat["properties"]["population"] = f"{int(data['PTOT']):,}".replace(",", " ")

update_geojson_props(df)

def color_status(props):
    if props["ligne_grande_vitesse"] and props["desserte_tgv"]:
        return "blue"
    elif props["desserte_tgv"] and not props["ligne_grande_vitesse"]:
        return "green"
    elif props["ligne_grande_vitesse"] and not props["desserte_tgv"]:
        return "orange"
    return "lightgray"

# Création de la carte Folium
def create_map():
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

    # Ajouter couche LGV à la carte Folium avec style (ligne rouge)
    folium.GeoJson(
        lgv_geojson,
        name="Lignes LGV",
        style_function=lambda feature: {
            'color': 'red',
            'weight': 3,
            'opacity': 0.8
        }
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

st.title("Desserte TGV simplifiée des départements français et population couverte")

st.markdown("""
- Bleu: Département avec ligne LGV  
- Vert : Département avec desserte TGV  
- Orange : Département traversé par LGV sans desserte  
- Gris : Département sans desserte ni LGV
""")

with st.expander("🗺️ Détail des départements (édition possible)", expanded=False):
    update = False
    edited_lgv = []
    edited_desserte = []
    st.markdown("Cochez les cases pour modifier la présence de **LGV** et/ou de **desserte TGV** dans chaque département :")
    
    header_cols = st.columns([1, 3, 2, 2, 2])
    header_cols[0].markdown("**Code**")
    header_cols[1].markdown("**Département**")
    header_cols[2].markdown("**Population**")
    header_cols[3].markdown("**LGV**")
    header_cols[4].markdown("**Desserte TGV**")
    st.markdown("---")

    for i, row in df.iterrows():
        cols = st.columns([1, 3, 2, 2, 2])
        cols[0].write(row['DEP'])
        cols[1].write(row['Département'])
        cols[2].write(f"{int(row['PTOT']):,}".replace(",", " "))
        key_lgv = f"lgv_{row['DEP']}"
        val_lgv = cols[3].checkbox("LGV", value=st.session_state.lgv_vals[i], key=key_lgv, label_visibility="collapsed")
        key_dtv = f"desserte_{row['DEP']}"
        val_dtv = cols[4].checkbox("Desserte TGV", value=st.session_state.desserte_vals[i], key=key_dtv, label_visibility="collapsed")
        edited_lgv.append(val_lgv)
        edited_desserte.append(val_dtv)
        if val_lgv != df.loc[i, 'ligne_grande_vitesse'] or val_dtv != df.loc[i, 'desserte_tgv']:
            update = True

    if update:
        df['ligne_grande_vitesse'] = edited_lgv
        df['desserte_tgv'] = edited_desserte
        st.session_state.lgv_vals = edited_lgv
        st.session_state.desserte_vals = edited_desserte
        update_geojson_props(df)
        st.success("✅ Données mises à jour sur la carte !")

# Créer et afficher la carte avec les données mises à jour
map_ = create_map()
st_folium(map_, width=800, height=600)

# Recalcul des pourcentages avec données modifiées
pop_total = df['PTOT'].sum()
pop_lgv = df.loc[df['ligne_grande_vitesse'], 'PTOT'].sum()
pop_desserte = df.loc[df['desserte_tgv'], 'PTOT'].sum()
pop_traverse_sans_desserte = df.loc[(df['ligne_grande_vitesse']) & (~df['desserte_tgv']), 'PTOT'].sum()
pop_aucune = df.loc[(~df['ligne_grande_vitesse']) & (~df['desserte_tgv']), 'PTOT'].sum()

# --- Pourcentage de population couverte (version à deux colonnes)
st.subheader("📊 Pourcentage de population couverte")
st.metric("Population totale", f"{pop_total:,}".replace(",", " "))

col1, col2 = st.columns(2)

# ---- Colonne 1 : départements avec desserte
with col1:
    st.markdown("### 🚄 Avec desserte / LGV")
    st.metric("Avec ligne LGV", f"{pop_lgv / pop_total * 100:.2f} %")
    st.metric("Avec desserte TGV", f"{pop_desserte / pop_total * 100:.2f} %")

# ---- Colonne 2 : départements sans desserte
with col2:
    st.markdown("### ⚪ Sans desserte")
    st.metric("Traversé par LGV sans desserte", f"{pop_traverse_sans_desserte / pop_total * 100:.2f} %")
    st.metric("Sans desserte ni LGV", f"{pop_aucune / pop_total * 100:.2f} %")