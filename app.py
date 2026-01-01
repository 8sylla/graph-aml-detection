import streamlit as st
from neo4j import GraphDatabase
from streamlit_agraph import agraph, Node, Edge, Config

# --- CONFIGURATION ---
st.set_page_config(page_title="AML Graph Detector", layout="wide")
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

# --- FONCTIONS UTILES ---
def get_driver():
    return GraphDatabase.driver(URI, auth=AUTH)

def get_suspicious_clients(driver):
    """Récupère la liste des clients à risque pour la sidebar"""
    # CORRECTION ICI : Ajout de "AS ..." pour avoir des clés propres
    query = """
    MATCH (c:Client) 
    WHERE c.risk_score > 0 
    RETURN c.id AS id, c.name AS name, c.risk_score AS risk_score, c.status AS status 
    ORDER BY c.risk_score DESC LIMIT 20
    """
    with driver.session() as session:
        return session.run(query).data()

def get_client_details(driver, client_id):
    """Récupère les infos d'un client spécifique"""
    query = """
    MATCH (c:Client {id: $id})
    RETURN c.name as name, c.risk_score as score, c.status as status, c.flags as flags
    """
    with driver.session() as session:
        result = session.run(query, id=client_id).single()
        return result if result else None

def get_graph_data(driver, client_id):
    """Récupère le sous-graphe autour du client (Niveau 2)"""
    # On cherche le client, ses comptes, et les transactions entrantes/sortantes
    query = """
    MATCH path = (c:Client {id: $id})-[:POSSEDE]->(a:Account)-[t:VIRE_VERS*1..2]-(other)
    RETURN path LIMIT 50
    """
    nodes = []
    edges = []
    node_ids = set()

    with driver.session() as session:
        results = session.run(query, id=client_id)
        
        for record in results:
            path = record['path']
            # Parcours des noeuds du chemin
            for node in path.nodes:
                if node.element_id not in node_ids:
                    n_type = list(node.labels)[0]
                    
                    # Style visuel selon le type
                    color = "#97C2FC" # Bleu par défaut
                    size = 25
                    label = "Node"
                    image = ""

                    if n_type == "Client":
                        color = "#FF6B6B" if node.get('status') == 'CRITICAL' else "#4AD395"
                        label = node.get('name', 'Client')
                        size = 30
                    elif n_type == "Account":
                        color = "#FFD166"
                        label = node.get('iban', 'Account')[:8] + "..."
                    elif n_type == "Bank":
                        color = "#118AB2"
                        label = node.get('name', 'Bank')

                    nodes.append(Node(
                        id=node.element_id, 
                        label=label, 
                        size=size, 
                        color=color
                    ))
                    node_ids.add(node.element_id)

            # Parcours des relations du chemin
            for rel in path.relationships:
                edges.append(Edge(
                    source=rel.start_node.element_id,
                    target=rel.end_node.element_id,
                    label=rel.type,
                    color="#cccccc"
                ))
                
    return nodes, edges

# --- INTERFACE UTILISATEUR ---

st.title("🕵️‍♂️ AML Graph Detector")
st.markdown("Système d'Aide à la Décision pour la lutte Anti-Blanchiment")

driver = get_driver()

# Sidebar : Liste des suspects
st.sidebar.header("Alertes Récentes")
suspects = get_suspicious_clients(driver)

selected_client_id = None

# Création des boutons dans la sidebar
for s in suspects:
    label = f"{s['name']} (Score: {s['risk_score']})"
    # CORRECTION ICI : on utilise s['id'] au lieu de s['c.id']
    if st.sidebar.button(label, key=s['id']): 
        selected_client_id = s['id']

# Si aucun sélectionné, on prend le premier de la liste
if not selected_client_id and suspects:
    # CORRECTION ICI : on utilise s['id'] au lieu de s['c.id']
    selected_client_id = suspects[0]['id']

# --- ZONE PRINCIPALE ---
if selected_client_id:
    details = get_client_details(driver, selected_client_id)
    
    # En-tête du profil
    col1, col2, col3 = st.columns(3)
    col1.metric("Client", details['name'])
    col2.metric("Score de Risque", details['score'])
    
    status_color = "green"
    if details['status'] == 'WARNING': status_color = "orange"
    if details['status'] == 'CRITICAL': status_color = "red"
    
    col3.markdown(f"### Statut : :{status_color}[{details['status']}]")

    # Affichage des Flags (Raisons de la suspicion)
    if details['flags']:
        st.write("🚩 **Indicateurs de détection :**")
        for flag in details['flags']:
            st.error(f"DETECTION : {flag}")

    # Visualisation du Graphe
    st.subheader("🕸️ Analyse Réseau (Graph Exploration)")
    with st.spinner("Chargement du graphe relationnel..."):
        nodes, edges = get_graph_data(driver, selected_client_id)
        
        if nodes:
            config = Config(width=800, height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
            # C'est ici que l'interactivité se joue
            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.info("Aucune transaction trouvée pour ce client.")

else:
    st.info("Aucun client suspect détecté dans la base. Lancez le générateur de fraude !")

driver.close()