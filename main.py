from FullNode import FullNode

fullNode = FullNode()

print("snapshot transactions: 현재 처리된 트랜잭션 정보\n"
      + "snapshot utxoset: 현재 UTXOset 정보\n")

while True:
    query = input("% ")
    if query == "snapshot transactions":
        info = fullNode.processedTransactionInfo
        for i in range(len(info)):
            txid, result = info[i]
            print(f"transction{i}: {txid}, validity check: {result}")
        print()

    elif query == "snapshot utxoset":
        utxoSet = fullNode.UTXOSet
        i = 0
        for key, utxo in utxoSet.items():
            print(f"utxo{i}: {utxo["txid"]}, {utxo["vout"]}, {utxo["value"]}, {utxo["scriptPubKey"]}")
            i += 1
        print()

    else:
        print("Invalid query entered")
        break