from neo4j import GraphDatabase

class FraudDetector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_detection_pipeline(self):
        """Lance toutes les règles de détection séquentiellement"""
        print("\n--- Démarrage du Moteur d'Inférence ---")
        
        with self.driver.session() as session:
            # 0. Reset des scores de risque
            print("1. Réinitialisation des scores...")
            session.run("MATCH (c:Client) SET c.risk_score = 0, c.flags = []")
            session.run("MATCH (t:Transaction) SET t.is_suspicious = false")

            # 1. Règle : Gros Montants (> 10,000)
            print("2. Analyse : Transactions à haut montant...")
            self._detect_high_amounts(session, threshold=10000)

            # 2. Règle : Smurfing (Beaucoup de petites transactions rapides)
            print("3. Analyse : Smurfing (Structuration)...")
            self._detect_smurfing(session)

            # 3. Règle : Cycles de Blanchiment (A -> B -> C -> A)
            print("4. Analyse : Cycles de blanchiment (Graph Algo)...")
            self._detect_laundering_cycles(session)

            # 4. Calcul final et classification
            print("5. Classification des Clients...")
            self._update_client_status(session)
            
        print("--- Analyse terminée ---")

    def _detect_high_amounts(self, session, threshold):
        """Flag les transactions supérieures au seuil"""
        query = """
        MATCH (c:Client)-[:POSSEDE]->(a:Account)-[t:VIRE_VERS]->(target)
        WHERE t.montant >= $threshold
        SET t.is_suspicious = true, t.reason = 'High Amount'
        SET c.risk_score = c.risk_score + 20
        SET c.flags = c.flags + 'HIGH_AMOUNT'
        RETURN count(t) as count
        """
        result = session.run(query, threshold=threshold)
        print(f"   -> {result.single()['count']} transactions suspectes détectées.")

    def _detect_smurfing(self, session):
        """
        Détecte si un compte fait beaucoup de petits virements (>5) 
        vers des bénéficiaires différents.
        """
        query = """
        MATCH (c:Client)-[:POSSEDE]->(a:Account)-[t:VIRE_VERS]->(other)
        WHERE t.montant < 3000
        WITH c, a, count(t) as num_tx
        WHERE num_tx > 5
        SET c.risk_score = c.risk_score + 30
        SET c.flags = c.flags + 'POTENTIAL_SMURFING'
        RETURN count(c) as count
        """
        result = session.run(query)
        print(f"   -> {result.single()['count']} cas de Smurfing détectés.")

    def _detect_laundering_cycles(self, session):
        """
        C'est LA force du Graphe. Trouver des cycles fermés.
        A -> B -> C -> A
        """
        # On cherche des chemins de longueur 3 à 5 qui reviennent au point de départ
        query = """
        MATCH path = (a:Account)-[:VIRE_VERS*3..5]->(a)
        WITH nodes(path) as accounts
        UNWIND accounts as acc
        MATCH (c:Client)-[:POSSEDE]->(acc)
        SET c.risk_score = c.risk_score + 50
        SET c.flags = c.flags + 'LAUNDERING_CYCLE'
        RETURN count(DISTINCT c) as count
        """
        result = session.run(query)
        print(f"   -> {result.single()['count']} participants à des cycles détectés.")

    def _update_client_status(self, session):
        """Met à jour le statut final (Vert/Orange/Rouge)"""
        query = """
        MATCH (c:Client)
        WHERE c.risk_score > 0
        SET c.status = CASE 
            WHEN c.risk_score >= 50 THEN 'CRITICAL'
            WHEN c.risk_score >= 20 THEN 'WARNING'
            ELSE 'SAFE'
        END
        """
        session.run(query)