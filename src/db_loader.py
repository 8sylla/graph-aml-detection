from neo4j import GraphDatabase
from tqdm import tqdm

class GraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clean_database(self):
        """ATTENTION: Efface toute la base de données"""
        print("Cleaning Database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def create_constraints(self):
        """Crée des index pour optimiser les performances"""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Client) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.iban IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE"
        ]
        with self.driver.session() as session:
            for q in queries:
                session.run(q)

    def load_data(self, df_clients, df_accounts, df_transactions):
        with self.driver.session() as session:
            
            # 1. Création des Clients
            print("Loading Clients to Neo4j...")
            query_client = """
            UNWIND $rows AS row
            CREATE (c:Client {id: row.client_id, name: row.name, risk: row.risk_score})
            """
            self._batch_run(session, query_client, df_clients)

            # 2. Création des Comptes et Relations (Client)-[:HAS_ACCOUNT]->(Account)
            print("Loading Accounts and linking to Clients...")
            query_account = """
            UNWIND $rows AS row
            MATCH (c:Client {id: row.client_id})
            MERGE (b:Bank {name: row.bank_name})
            CREATE (a:Account {iban: row.account_id, balance: row.balance})
            CREATE (c)-[:POSSEDE]->(a)
            CREATE (a)-[:DOMICILIE_CHEZ]->(b)
            """
            self._batch_run(session, query_account, df_accounts)

            # 3. Création des Transactions (Account)-[:VIRE]->(Account)
            print("Loading Transactions...")
            query_tx = """
            UNWIND $rows AS row
            MATCH (source:Account {iban: row.sender_iban})
            MATCH (target:Account {iban: row.receiver_iban})
            CREATE (source)-[t:VIRE_VERS {
                id: row.tx_id, 
                montant: row.amount, 
                date: row.date
            }]->(target)
            """
            self._batch_run(session, query_tx, df_transactions)

    def _batch_run(self, session, query, df, batch_size=1000):
        """Exécute les requêtes par lots pour ne pas saturer la RAM"""
        total = len(df)
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size].to_dict('records')
            session.run(query, rows=batch)

    def inject_fraud_ring(self):
        """Crée manuellement un cycle de fraude évident A->B->C->A"""
        print("Injecting explicit Fraud Ring for demo...")
        query = """
        CREATE (c1:Client {id:'FRAUD_1', name:'M. White', risk_score:0})
        CREATE (c2:Client {id:'FRAUD_2', name:'M. Pink', risk_score:0})
        CREATE (c3:Client {id:'FRAUD_3', name:'M. Blue', risk_score:0})
        
        CREATE (a1:Account {iban:'FR_FRAUD_1', balance:0})-[:DOMICILIE_CHEZ]->(:Bank {name:'Mafia Bank'})
        CREATE (a2:Account {iban:'FR_FRAUD_2', balance:0})-[:DOMICILIE_CHEZ]->(:Bank {name:'Mafia Bank'})
        CREATE (a3:Account {iban:'FR_FRAUD_3', balance:0})-[:DOMICILIE_CHEZ]->(:Bank {name:'Mafia Bank'})
        
        CREATE (c1)-[:POSSEDE]->(a1)
        CREATE (c2)-[:POSSEDE]->(a2)
        CREATE (c3)-[:POSSEDE]->(a3)
        
        // Le cycle
        CREATE (a1)-[:VIRE_VERS {amount: 15000, date: '2024-01-01', is_suspicious:false}]->(a2)
        CREATE (a2)-[:VIRE_VERS {amount: 14000, date: '2024-01-02', is_suspicious:false}]->(a3)
        CREATE (a3)-[:VIRE_VERS {amount: 13000, date: '2024-01-03', is_suspicious:false}]->(a1)
        """
        with self.driver.session() as session:
            session.run(query)