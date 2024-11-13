import json
from dotenv import load_dotenv
import os

load_dotenv()

class FullNode:
    def __init__(self):
        self.transactionSet = dict()    # 검색, 삭제를 용이하게 하기 위해 딕셔너리로 생성
        self.UTXOSet = dict()

        # 트랜잭션 파일을 읽어 Transaction set에 저장
        with open(os.getenv('TRANSITION_FILE_PATH')) as f:
            transactions = json.load(f)["transactions"]
            for transaction in transactions:
                txid = transaction["txid"]
                if (self.transactionSet.get(txid) == None): # 중복 방지를 위한 확인
                    self.transactionSet[txid] = transaction

        # UTXO 파일을 읽어 UTXO set에 저장
        with open(os.getenv('UTXO_FILE_PATH')) as f:
            utxoes = json.load(f)["utxos"]
            for utxo in utxoes:
                txid = utxo["txid"] + ':' + str(utxo["vout"])
                if (self.UTXOSet.get(txid) == None):    # 중복 방지를 위한 확인
                    self.UTXOSet[txid] = utxo

testNode = FullNode()
print(testNode.transactionSet)
print(testNode.UTXOSet)