from src.generator import DataGenerator
from src.db_loader import GraphDB
import os

# Configuration Neo4j
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def main():
    print("--- Démarrage du Projet Graph AML ---")
    
    # 1. Génération des données
    gen = DataGenerator(num_clients=200, num_banks=5)
    df_clients = gen.generate_clients()
    df_accounts = gen.generate_accounts()
    # On génère beaucoup de transactions pour avoir un graphe dense
    df_transactions = gen.generate_transactions(num_transactions=1000)

    print(f"Data Generated: {len(df_clients)} clients, {len(df_transactions)} transactions.")

    # 2. Connexion à la DB
    db = GraphDB(URI, AUTH[0], AUTH[1])

    try:
        # 3. Nettoyage et Préparation
        db.clean_database()
        db.create_constraints()

        # 4. Injection
        db.load_data(df_clients, df_accounts, df_transactions)
        
        print("\n--- SUCCÈS : Base de données construite ! ---")
        print("Ouvrez http://localhost:7474 et lancez la requête : MATCH (n) RETURN n LIMIT 50")

    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()