import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        #Cria o bloco genesis
        self.new_block(previous_hash='1', proof=100)

    """
    Add um novo nó a lista de nós
    """

    def register_node(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('URL Invalido')

    """
    Determina de o blockchain dado eh valido 
    """

    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof'], last_block['previous_hash']):
                return False

            last_block = block
            current_index += 1

        return True

    """
    Algoritmo consensus, ele resolve conflitos, trocando nossa chain pela maior na rede
    """

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


    # Cria um bloco em uma blockchain
    # Proof é um int e é a prova dada pelo algoritmo de Proof of Work
    # Previous_hasg é uma string opcional do hash do bloco anterior
    # Retorna um novo bloco

    def new_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset a lista atual de transações
        self.current_transactions = []

        self.chain.append(block)
        return block


    # Add transação a um bloco
    # Esse metodo retorna um int que eh o index do bloco que tera essa transação
    # Os parametro sender e recipient são string e o amount eh um int

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

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
    def proof_of_work(self, last_block):
        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    # Verifica se o hash(last_proff, proof) contem 4 zeros a esquerda
    # Os parametros sao int e o metodo retorna um booelan
    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

# Instancia nosso Nó
app = Flask(__name__)

# Gera um endereço global unico para o nó
node_identifier = str(uuid4()).replace('-', '')

# Instancia a Blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # Roda o algoritmo de proof of work para pegar a proxima prova...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # Recebe uma recompensa por encontrar a prova
    # Quem está enviando é "0" para mostrar que esse nó minerou uma nova moeda.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Add o novo Block a cadeia (chain)
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Novo bloco adicionado",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Checa se todos os valores necessarios estao no POST
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Informacao faltando', 400

    # Cria nova transação
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transacao será adicionada ao Bloco {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Forneca uma lista valida de nos", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'Novos nos foram adicionados',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Nossa cadeia foi substituida',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Nossa cadeia eh autoritaria',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)
