import hashlib
import json
from time import time

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transaction = []

        #Cria o bloco genesis
        self.new_block(previous_hash=1, proof=100)

    # Cria um bloco em uma blockchain
    # Proof é um int e é a prova dada pelo algoritmo de Proof of Work
    # Previous_hasg é uma string opcional do hash do bloco anterior
    # Retorna um novo bloco
    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transaction': self.current_transaction,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        #Reset a lista atual de transações
        self.current_transaction = []
        self.chain.append(block)
        return block


    # Add transação a um bloco
    # Esse metodo retorna um int que eh o index do bloco que tera essa transação
    # Os parametro sender e recipient são string e o amount eh um int
    def new_transaction(self, sender, recipient, amount):
        self.current_transaction.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index']+1

    @property
    def last_block(self):
        return self.chain[-1]

    # Cria um hash para o block (SHA-256)
    # Retorna uma string
    @staticmethod
    def hash(block):
        # Ordena o dicionario, para ter certeza que nao havera inconsistencia nos hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # Encontre um numero P' que Hash(pP') contem 4 zeros a esquerda, onde p é o P' anterior.
    # p é a proof anterior e P' é a nova proof.
    # last_proof é um int e o metodo retorna um int
    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    # Verifica se o hash(last_proff, proof) contem 4 zeros a esquerda
    # Os parametros sao int e o metodo retorna um booelan
    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
