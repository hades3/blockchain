import json, os, hashlib
from dotenv import load_dotenv
from ecdsa import SigningKey, VerifyingKey, SECP256k1

load_dotenv()

class FullNode:
    def __init__(self):
        self.transactionSet = dict()  # 검색, 삭제를 용이하게 하기 위해 딕셔너리로 생성
        self.UTXOSet = dict()
        self.processedTransactionInfo = list()

        # 트랜잭션 파일을 읽어 Transaction set에 저장
        with open(os.getenv('TRANSITION_FILE_PATH')) as f:
            transactions = json.load(f)["transactions"]
            for transaction in transactions:
                txid = transaction["txid"]
                if self.transactionSet.get(txid) is None:  # 중복 방지를 위한 확인
                    self.transactionSet[txid] = transaction

        # UTXO 파일을 읽어 UTXO set에 저장
        with open(os.getenv('UTXO_FILE_PATH')) as f:
            utxoes = json.load(f)["utxos"]
            for utxo in utxoes:
                key = utxo["txid"] + ':' + str(utxo["vout"])
                if self.UTXOSet.get(key) is None:  # 중복 방지를 위한 확인
                    self.UTXOSet[key] = utxo

        self.verify_utxo()

    # output을 utxo 집합에 추가하기 위해 형식 변환
    def output_to_utxo(self, txid, output):
        result = {
            "txid": txid,
            "vout": output["n"],
            "value": output["value"],
            "scriptPubKey": output["scriptPubKey"],
        }
        return result

    # sha256, ripemd160 해시
    def hash160(self, data):
        sha256_hash = hashlib.sha256(data.encode("utf-8")).digest()  # 해싱한 바이트 문자열 반환
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).hexdigest()  # 해싱한 바이트 문자열을 16진수로 변환
        return ripemd160_hash

    # 트랜잭션에서 scriptSig 제외
    def exclude_scriptSig(self, transaction_json):
        result = {
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

        return json.dumps(result)

    # 서명 검증
    def verify_signature(self, transaction, sig, pubKey):
        # 트랜잭션에서 scriptSig 제외
        exclude_scriptSig_transaction = self.exclude_scriptSig(transaction)
        # 해시
        hashed_exclude_scriptSig_transaction = self.hash160(exclude_scriptSig_transaction)
        # 바이트로 변환
        hashed_exclude_scriptSig_transaction = bytes.fromhex(hashed_exclude_scriptSig_transaction)

        # 문자열로 전달된 sig를 bytes로 변환
        sig = bytes.fromhex(sig)

        # 문자열로 전달된 pubKey를 객체로 변환
        pubKey = VerifyingKey.from_string(bytes.fromhex(pubKey), curve=SECP256k1)

        # 검증
        try:
            if pubKey.verify(sig, hashed_exclude_scriptSig_transaction):
                return "TRUE"
            else:
                return "FALSE"
        except Exception:
            return "FALSE"

    def verify_amount(self, transaction):
        utxo_sum = 0
        output_sum = 0

        for input in transaction["vin"]:
            key = input["txid"] + ':' + str(input["vout"])
            if self.UTXOSet.get(key) is None:
                print(transaction)
                print("valid check: failed, utxo not exist")
                self.processedTransactionInfo.append((transaction["txid"], "failed"))
                return False

            utxo = self.UTXOSet.get(key)
            utxo_sum += utxo["value"]

        for output in transaction["vout"]:
            output_sum += output["value"]

        if utxo_sum >= output_sum:
            return True
        else:
            print(transaction)
            print("valid check: failed, Not enough money")
            self.processedTransactionInfo.append((transaction["txid"], "failed"))
            return False

    def verify_script(self, transaction, unlocking_script, locking_script):
        locking_script = locking_script.split()
        stack = []
        failed_inst = "NONE"
        flag = 1  # 1이면 고려, 0이면 무시

        # for P2SH
        if locking_script[-1] == "EQUALVERIFY":
            stack.append(unlocking_script)
        # else
        else:
            for element in unlocking_script.split():
                stack.append(element)

        for element in locking_script:

            # IF
            if element == "IF":
                stack_top = stack.pop()
                if stack_top == "TRUE":
                    flag = 1
                elif stack_top == "FALSE":
                    flag = 0
                continue
            # ELSE
            elif element == "ELSE":
                flag = abs(flag - 1)
                continue
            # ENDIF
            elif element == "ENDIF":
                flag = 1
                continue

            # 조건문 결과에 따른 흐름 제어
            if flag == 0:
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
                    failed_inst = element
                    stack.append("FALSE")
            # EQUALVERIFY
            elif element == "EQUALVERIFY":
                stack_top_first = stack.pop()
                stack_top_second = stack.pop()
                if stack_top_first != stack_top_second:
                    failed_inst = element
                    return False, failed_inst
                else:
                    failed_inst = "NONE"
            # CHECKSIG
            elif element == "CHECKSIG":
                pubKey = stack.pop()
                sig = stack.pop()
                if self.verify_signature(transaction, sig, pubKey) == "TRUE":
                    stack.append("TRUE")
                else:
                    failed_inst = element
                    stack.append("FALSE")
            # CHECKSIGVERIFY
            elif element == "CHECKSIGVERIFY":
                pubKey = stack.pop()
                sig = stack.pop()
                if self.verify_signature(transaction, sig, pubKey) != "TRUE":
                    failed_inst = element
                    return False, failed_inst
            # CHECKMULTISIG
            elif element == "CHECKMULTISIG":
                n = int(stack.pop())
                pubKeys = [stack.pop() for _ in range(n)]
                m = int(stack.pop())
                for i in range(m):
                    sig = stack.pop()
                    for j in range(n):
                        if self.verify_signature(transaction, sig, pubKeys[j]) == "TRUE":
                            m -= 1
                            break
                if m <= 0:
                    failed_inst = "NONE"
                    stack.append("TRUE")
                else:
                    failed_inst = element
                    stack.append("FALSE")
            elif element == "CHECKMULTISIGVERIFY":
                n = int(stack.pop())
                pubKeys = [stack.pop() for _ in range(n)]
                m = int(stack.pop())
                for i in range(m):
                    sig = stack.pop()
                    for j in range(n):
                        if self.verify_signature(transaction, sig, pubKeys[j]) == "TRUE":
                            m -= 1
                            break
                if m <= 0:
                    failed_inst = "NONE"
                else:
                    failed_inst = element
                    return False, failed_inst
            else:
                stack.append(element)

        if locking_script[-1] == "EQUALVERIFY":
            if len(stack) == 1 and stack.pop() == unlocking_script:
                return self.verify_script(transaction, "", unlocking_script)
        else:
            if len(stack) == 1 and stack.pop() == "TRUE":
                return True, failed_inst
            else:
                return False, failed_inst

    def verify_utxo(self):
        for transaction_txid in self.transactionSet:
            transaction = self.transactionSet[transaction_txid]

            verify_result = True

            # 금액 검증이 실패하면, 실패 메세지 출력
            if self.verify_amount(transaction) is False:
                break

            # 스크립트 검증
            for input in transaction["vin"]:

                key = input["txid"] + ':' + str(input["vout"])

                unlocking_script = input["scriptSig"]
                locking_script = self.UTXOSet[key]["scriptPubKey"]

                verify_result, failed_inst, = self.verify_script(transaction, unlocking_script, locking_script)

                if verify_result is False:
                    print(transaction)
                    self.processedTransactionInfo.append((transaction_txid, "failed"))
                    print("validity check: failed at", failed_inst)
                    print()
                    break

            if verify_result is False:
                continue
            # 모든 UTXO가 검증을 통과하면, UTXO들을 UTXOset에서 제거하고, output들을 UTXOset에 추가
            print(transaction)

            for input in transaction["vin"]:
                key = input["txid"] + ':' + str(input["vout"])
                self.UTXOSet.pop(key)

            for output in transaction["vout"]:
                key = transaction_txid + ':' + str(output["n"])
                if self.UTXOSet.get(key) is None:
                    self.UTXOSet[key] = self.output_to_utxo(transaction_txid, output)

            self.processedTransactionInfo.append((transaction_txid, "passed"))
            print("validity check: passed")
            print()

        
testNode = FullNode()
print(testNode.UTXOSet)
