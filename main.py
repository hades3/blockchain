from FullNode import FullNode

fullNode = FullNode()

while True:
    query = input()

    if query == "snapshot transactions":
        info = fullNode.processedTransactionInfo
        for i in range(len(info)):
            txid, result = info[i]
            print(f"transction{i}: {txid}, validity check: {result}")

    elif query == "snapshot utxoset":
        utxoSet = fullNode.UTXOSet
        i = 0
        for key, utxo in utxoSet.items():
            print(f"utxo{i}: {utxo["txid"]}, {utxo["vout"]}, {utxo["value"]}, {utxo["scriptPubKey"]}")
            i += 1

    else:
        print("Invalid query entered")