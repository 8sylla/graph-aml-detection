import random
from faker import Faker
import pandas as pd
from datetime import datetime, timedelta

fake = Faker('fr_FR') # Données françaises

class DataGenerator:
    def __init__(self, num_clients=100, num_banks=5):
        self.num_clients = num_clients
        self.num_banks = num_banks
        self.clients = []
        self.accounts = []
        self.transactions = []

    def generate_clients(self):
        """Génère des profils clients"""
        print(f"Generating {self.num_clients} clients...")
        for _ in range(self.num_clients):
            client = {
                'client_id': fake.uuid4(),
                'name': fake.name(),
                'address': fake.address().replace('\n', ', '),
                'birth_date': fake.date_of_birth(minimum_age=18, maximum_age=90).isoformat(),
                'risk_score': random.choice(['LOW', 'MEDIUM', 'HIGH']) # Score initial aléatoire
            }
            self.clients.append(client)
        return pd.DataFrame(self.clients)

    def generate_accounts(self):
        """Chaque client reçoit 1 ou 2 comptes bancaires"""
        print("Generating accounts...")
        banks = [fake.company() + " Bank" for _ in range(self.num_banks)]
        
        for client in self.clients:
            num_accounts = random.randint(1, 2)
            for _ in range(num_accounts):
                account = {
                    'account_id': fake.iban(),
                    'client_id': client['client_id'],
                    'bank_name': random.choice(banks),
                    'balance': round(random.uniform(1000, 50000), 2),
                    'creation_date': fake.date_this_decade().isoformat()
                }
                self.accounts.append(account)
        return pd.DataFrame(self.accounts)

    def generate_transactions(self, num_transactions=500):
        """Génère des transactions entre les comptes existants"""
        print(f"Generating {num_transactions} transactions...")
        account_ids = [acc['account_id'] for acc in self.accounts]
        
        for _ in range(num_transactions):
            sender = random.choice(account_ids)
            receiver = random.choice(account_ids)
            
            # Éviter qu'on s'envoie de l'argent à soi-même
            while receiver == sender:
                receiver = random.choice(account_ids)

            tx = {
                'tx_id': fake.uuid4(),
                'sender_iban': sender,
                'receiver_iban': receiver,
                'amount': round(random.uniform(10, 15000), 2),
                'date': fake.date_time_between(start_date='-1y', end_date='now').isoformat(),
                'currency': 'EUR'
            }
            self.transactions.append(tx)
        return pd.DataFrame(self.transactions)
    