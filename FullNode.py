import json, os, hashlib, base64
from dotenv import load_dotenv
from ecdsa import SigningKey, VerifyingKey, SECP256k1

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
                if self.transactionSet.get(txid) is None: # 중복 방지를 위한 확인
                    self.transactionSet[txid] = transaction

        # UTXO 파일을 읽어 UTXO set에 저장
        with open(os.getenv('UTXO_FILE_PATH')) as f:
            utxoes = json.load(f)["utxos"]  
            for utxo in utxoes:
                key = utxo["txid"] + ':' + str(utxo["vout"])
                if self.UTXOSet.get(key) is None:    # 중복 방지를 위한 확인
                    self.UTXOSet[key] = utxo

    # sha256, ripemd160 해시
    def hash160(self, target):
        sha256_hash = hashlib.sha256(target.encode("utf-8")).digest()   # 해싱한 바이트 문자열 반환
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).hexdigest()  # 해싱한 바이트 문자열을 16진수로 변환
        return ripemd160_hash

    # 트랜잭션에서 scriptSig 제외
    def exclude_scriptSig(self, transaction_json):
        result = {
            "txid": transaction_json["txid"],
            "hash": transaction_json["hash"],
            "version": transaction_json["version"],
            "size": transaction_json["size"],
            "locktime": transaction_json["locktime"],
            "vin": [],
            "vout": transaction_json["vout"],
            "blockhash": transaction_json["blockhash"],
            "confirmations": transaction_json["confirmations"],
            "time": transaction_json["time"],
            "blocktime": transaction_json["blocktime"]
        }

        for vin in transaction_json["vin"]:
            vin_data = {key: value for key, value in vin.items() if key != "scriptSig"}
            result["vin"].append(vin_data)

        return result

    def verify_utxo(self):
        for transaction_txid in self.transactionSet:
            for utxo in self.transactionSet[transaction_txid]["vin"]:
                stack = []

                key = utxo["txid"] + ':' + str(utxo["vout"])
                if self.UTXOSet.get(key) is None:
                    continue

                unlocking_script = utxo["scriptSig"].split()
                locking_script = self.UTXOSet[key]["scriptPubKey"].split()
                condition_result = "NONE"

                for element in unlocking_script:
                    stack.append(element)

                for element in locking_script:
                    print(element)
                    if condition_result == "FALSE":
                        if element == "ELSE":
                            condition_result = True
                        continue

                    # DUP
                    if element == "DUP":
                        stack.append(stack[-1])
                    # HASH
                    elif element == "HASH":
                        stack_top = stack.pop()
                        stack.append(self.hash160(stack_top))
                    # EQUAL
                    elif element == "EQUAL":
                        stack_top_first = stack.pop()
                        stack_top_second = stack.pop()
                        if stack_top_first == stack_top_second:
                            stack.append("TRUE")
                        else:
                            stack.append("FALSE")
                    # EQUALVERIFY
                    elif element == "EQUALVERIFY":
                        stack_top_first = stack.pop()
                        stack_top_second = stack.pop()
                        if stack_top_first != stack_top_second:
                            break
                    # CHECKSIG
                    elif element == "CHECKSIG":
                        pubKey = stack.pop()
                        sig = stack.pop()
                        transaction = self.transactionSet[transaction_txid]
                        verify_result = self.verify_signature(transaction, sig, pubKey)
                        stack.append(verify_result)
                    # IF
                    elif element == "IF":
                        condition_result = stack.pop()
                    elif element == "ENDIF":
                        continue
                    else:
                        stack.append(element)

                # CHECKFINALRESULT
                if len(stack) == 1 and stack.pop() == "TRUE":
                    return "passed"
                else:
                    return "failed"

testNode = FullNode()
print(testNode.verify_utxo())