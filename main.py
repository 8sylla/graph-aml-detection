from src.generator import DataGenerator
from src.db_loader import GraphDB
from src.inference_engine import FraudDetector # <--- IMPORT DU NOUVEAU MODULE
import time

# Configuration
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def main():
    print("--- Démarrage du Projet Graph AML ---")
    
    # ÉTAPE 1 : GENERATION & CHARGEMENT (Déjà fait, mais on peut relancer)
    # Pour gagner du temps si la base est déjà pleine, commentez les lignes ci-dessous
    # -------------------------------------------------------------------
    print("\n[PHASE 1] Initialisation des données...")
    gen = DataGenerator(num_clients=300, num_banks=5)
    df_clients = gen.generate_clients()
    df_accounts = gen.generate_accounts()
    # On force plus de transactions pour être sûr d'avoir des cycles
    df_transactions = gen.generate_transactions(num_transactions=2000) 

    db = GraphDB(URI, AUTH[0], AUTH[1])
    try:
        db.clean_database()
        db.create_constraints()
        db.load_data(df_clients, df_accounts, df_transactions)
        db.inject_fraud_ring()
    finally:
        db.close()
    # -------------------------------------------------------------------

    time.sleep(1) # Petite pause

    # ÉTAPE 2 : DÉTECTION DE FRAUDE (LE MOTEUR D'INFÉRENCE)
    print("\n[PHASE 2] Analyse Intelligente...")
    detector = FraudDetector(URI, AUTH[0], AUTH[1])
    try:
        detector.run_detection_pipeline()
    except Exception as e:
        print(f"Erreur detection : {e}")
    finally:
        detector.close()

    print("\n--- PROJET TERMINÉ AVEC SUCCÈS ---")
    print("Pour vérifier, lancez cette requête dans Neo4j Browser :")
    print("MATCH (c:Client) WHERE c.status = 'CRITICAL' RETURN c LIMIT 10")

if __name__ == "__main__":
    main()