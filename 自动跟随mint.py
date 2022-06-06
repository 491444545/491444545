import json
import platform
import threading
import time
import requests
from blocknative.stream import Stream
from web3 import Web3
from eth_abi import decode_abi
import os

configExample = {
    "RPC": "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
    "privateKey": ["私钥1", "私钥2"],
    "blocknativeKey": "监控平台key",
    "barkKey": "IOS推送软件key",
    "scanApikey": "https://etherscan.io/register注册获取",
    "maxGasPrice": 50,
    "maxGasLimit": 1000000,
    "maxValue": 0,
    "follow": {
        "0x8888887a5e2491fec904d90044e6cd6c69f1e71c": {"start": 0, "end": 24},
        "0x555555B63d1C3A8c09FB109d2c80464685Ee042B": {"start": 18, "end": 6},
        "0x99999983c70de9543cdc11dB5DE66A457d241e8B": {"start": 8, "end": 20}
    },
    "blacklist": ["Ape", "Bear", "Duck", "Pixel", "Not", "Okay", "Woman", "Baby", "Goblin", "Ai"]
}

if platform.system().lower() == 'windows':
    import ctypes
    import sys

    std_out_handle = ctypes.windll.kernel32.GetStdHandle(-11)


    def set_cmd_text_color(color, handle=std_out_handle):
        Bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
        return Bool


    def print_color(message, color):
        colorDict = {'green': 0x0a, 'red': 0x0c, 'blue': 0x0b, 'yellow': 0x0e}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        set_cmd_text_color(colorDict[color])
        sys.stdout.write(f'[{stime}] {message}\n')
        set_cmd_text_color(0x0c | 0x0a | 0x09)
else:
    def print_color(message, color):
        colorDict = {'green': '32m', 'red': '31m', 'blue': '34m', 'yellow': '33m'}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        print(f'[{stime}] \033[1;{colorDict[color]}{message}\033[0m')


def bark(info, data):
    if barkKey != '':
        requests.get('https://api.day.app/' + barkKey + '/' + info + '?url=' + data)


def getETHPrice():
    params = {
        'module': 'stats',
        'action': 'ethprice',
        'apikey': scanApikey
    }
    res = requests.get('https://api.etherscan.io/api', params=params)
    if res.status_code == 200 and res.json()['status'] == '1':
        return float(res.json()['result']['ethusd'])


def getMethodName(methodSignature, _conadd, _pendingBlockNumber):
    try:
        if methodSignature in methodNameDict:
            print_color('mint方法：' + methodNameDict[methodSignature]['method'], 'blue')
            return methodNameDict[methodSignature]['isMint'], methodNameDict[methodSignature]['method']
        res = requests.get('https://www.4byte.directory/api/v1/signatures/?hex_signature=' + methodSignature)
        if res.status_code == 200 and res.json()['count'] > 0:
            method = res.json()['results'][0]['text_signature']
            methodName = method.split('(')[0].lower()
            print_color('mint方法：' + method, 'blue')
            if 'mint' in methodName:
                methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                return True, method
            else:
                if isMintFromBlock(_pendingBlockNumber, _conadd, methodSignature):
                    methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                    return True, method
                methodNameDict[methodSignature] = {'method': method, 'isMint': False}
        else:
            params = {
                'module': 'contract',
                'action': 'getabi',
                'address': _conadd,
                'apikey': scanApikey
            }
            res = requests.get('https://api.etherscan.io/api', params=params)
            if res.status_code == 200 and res.json()['status'] == '1':
                abi = res.json()['result']
                NFTcon = w3.eth.contract(address=w3.toChecksumAddress(_conadd), abi=abi)
                abiinfo = NFTcon.get_function_by_selector(methodSignature)
                method = str(abiinfo)[10:-1]
                print_color('mint方法：' + method, 'blue')
                if 'mint' in method.split('(')[0].lower():
                    methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                    return True, method
                else:
                    if isMintFromBlock(_pendingBlockNumber, _conadd, methodSignature):
                        methodNameDict[methodSignature] = {'method': method, 'isMint': True}
                        return True, method
                    methodNameDict[methodSignature] = {'method': method, 'isMint': False}
        return False, None
    except:
        return False, None


def isMintFromBlock(_block, _conadd, _methodSignature):
    try:
        log = w3.eth.filter({
            'fromBlock': _block - 10,
            'toBlock': _block - 1,
            'address': w3.toChecksumAddress(_conadd),
            'topics': ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
                       '0x0000000000000000000000000000000000000000000000000000000000000000']
        })
        txs = log.get_all_entries()
        if len(txs) > 1:
            transaction = w3.eth.get_transaction(txs[0]['transactionHash'])
            mintMethod = transaction['input'][:10]
            if _methodSignature == mintMethod:
                return True
    except Exception as e:
        print(str(e))
    return False


def isBlackList(_to):
    try:
        NFTcon = w3.eth.contract(address=_to, abi=[nameabi])
        name = NFTcon.functions.name().call()
        for black in blacklist:
            if black in name:
                print_color(name + "黑名单" + black + "，跳过", 'red')
                return False
    except:
        print_color('获取NFT名称失败，跳过', 'red')
        return False
    print_color('NFT名称：' + name, 'blue')
    return True


def isMintTime(_from):
    for _follow in follows:
        if _follow.lower() == _from.lower():
            starttime = int(follows[_follow]['start'])
            endtime = int(follows[_follow]['end'])
            tm_hour = time.localtime().tm_hour
            if tm_hour >= starttime or tm_hour < endtime:
                pass
            else:
                print_color("非Mint时间，跳过", 'red')
                return False
    return True


def getgas():
    headers = {"Authorization": blocknativeKey}
    url = 'https://api.blocknative.com/gasprices/blockprices?confidenceLevels=95'
    res = requests.get(url=url, headers=headers)
    if res.status_code == 200:
        estimatedPrices = res.json()['blockPrices'][0]['estimatedPrices'][0]
        maxPriorityFeePerGas = estimatedPrices['maxPriorityFeePerGas']
        maxFeePerGas = estimatedPrices['maxFeePerGas']
        baseFee = estimatedPrices['price']
        maxPriorityFeePerGas = w3.toWei(maxPriorityFeePerGas + 0.1, 'gwei')
        maxFeePerGas = w3.toWei(maxFeePerGas + 0.1, 'gwei')
        baseFee = w3.toWei(baseFee + 0.1, 'gwei')
        return baseFee, maxFeePerGas, maxPriorityFeePerGas


def minttx(_account, _privateKey, _inputData, _method, _from_address, _to_address, _maxFeePerGas, _maxPriorityFeePerGas, _value, _gasLimit):
    try:
        abi = _method.split('(')[1][:-1].split(',')
        if len(abi) != 0 and 'address' in abi:
            params = decode_abi(abi, bytes.fromhex(_inputData[10:]))
            for index in range(len(abi)):
                if abi[index] == 'address':
                    _inputData = _inputData.replace(params[index][2:].lower(), _account.address[2:].lower())
        transaction = {
            'from': _account.address,
            'chainId': chainId,
            'to': _to_address,
            'gas': _gasLimit,
            'maxFeePerGas': _maxFeePerGas,
            'maxPriorityFeePerGas': _maxPriorityFeePerGas,
            'nonce': w3.eth.getTransactionCount(_account.address),
            'data': _inputData,
            'value': _value
        }
        try:
            estimateGas = w3.eth.estimateGas(transaction)
            if estimateGas > _gasLimit:
                transaction['gas'] = int(estimateGas * 1.2)
        except Exception as e:
            if 'allowance' not in str(e):
                print_color('发送交易失败:' + str(e), 'red')
                return
        signed = w3.eth.account.sign_transaction(transaction, _privateKey)
        new_raw = signed.rawTransaction.hex()
        tx_hash = w3.eth.sendRawTransaction(new_raw)
        print_color("mint交易发送成功" + w3.toHex(tx_hash), 'green')
        freceipt = w3.eth.waitForTransactionReceipt(tx_hash, 600)
        if freceipt.status == 1:
            try:
                ETHused = freceipt.effectiveGasPrice * freceipt.gasUsed
                ETHused = float(w3.fromWei(ETHused, 'ether'))
                USDuse = ETHPrice * ETHused
                ETHusedinfo = '本次mint：' + str(USDuse) + ' U'
            except:
                ETHusedinfo = ''
            print_color("mint成功   " + ETHusedinfo, 'green')
            bark('mint成功', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
        else:
            print_color("mint失败", 'red')
            if _to_address in mintadd:
                mintadd.remove(_to_address)
            bark('mint失败', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
    except Exception as e:
        if _to_address in mintadd:
            mintadd.remove(_to_address)
        print_color('交易失败:' + str(e), 'red')
        return


async def txn_handler(txn, unsubscribe):
    to_address = txn['to']
    from_address = txn['from']
    to_address = w3.toChecksumAddress(to_address)
    inputData = txn['input']
    value = int(txn['value'])
    gasLimit = int(txn['gas'])
    tx_maxFeePerGas, tx_maxPriorityFeePerGas = 0, 0
    if 'maxFeePerGas' in txn:
        tx_maxFeePerGas = int(txn['maxFeePerGas'])
        tx_maxPriorityFeePerGas = int(txn['maxPriorityFeePerGas'])
    pendingBlockNumber = int(txn['pendingBlockNumber'])
    print_color(from_address + "监控到新交易", 'yellow')
    if not isMintTime(from_address):
        return
    if value > maxValue:
        print_color("超过最大金额，跳过", 'red')
        return
    if to_address in mintadd:
        print_color("mint过，跳过", 'red')
        return
    isMint, method = getMethodName(inputData[:10], to_address, pendingBlockNumber)
    if not isMint:
        print_color('可能不是mint交易,跳过', 'red')
        return
    if not isBlackList(to_address):
        return
    gasPrice, maxFeePerGas, maxPriorityFeePerGas = getgas()
    if gasPrice > maxGasPrice:
        print_color('gasPrice过高,跳过', 'red')
        return
    maxFeePerGas = maxFeePerGas if maxFeePerGas > tx_maxFeePerGas else tx_maxFeePerGas
    maxPriorityFeePerGas = maxPriorityFeePerGas if maxPriorityFeePerGas > tx_maxPriorityFeePerGas else tx_maxPriorityFeePerGas
    if gasPrice + maxPriorityFeePerGas < maxFeePerGas:
        maxFeePerGas = gasPrice + maxPriorityFeePerGas
    mintadd.append(to_address)
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], inputData, method, from_address, to_address, maxFeePerGas, maxPriorityFeePerGas, value, gasLimit)).start()


def main():
    while True:
        try:
            stream = Stream(blocknativeKey)
            print_color(str(len(accounts)) + '个地址开始监控', 'blue')
            print_color('开始监控', 'blue')
            for _follow in follows:
                filters = [{
                    "status": "pending",
                    "from": _follow
                }]
                stream.subscribe_address(_follow, txn_handler, filters)
            stream.connect()
        except Exception as e:
            print_color(str(e), 'red')
            time.sleep(10)


if __name__ == '__main__':
    print_color("有能力的请使用源码，不对使用者安全负责", 'red')
    print_color("打狗请用小号，无法保证无bug", 'red')
    print_color("开源地址：https://github.com/Fooyao/FollowMint", 'red')
    print_color("代码水平较差，有任何优化建议请反馈", 'red')
    if not os.path.exists('config.json'):
        print_color('请先配置config.json', 'blue')
        file = open('config.json', 'w')
        file.write(json.dumps(configExample))
        file.close()
        time.sleep(10)
    try:
        file = open('config.json', 'r')
        config = json.loads(file.read())
        RPC = config['RPC']
        privateKeys = config['privateKey']
        scanApikey = config['scanApikey']
        blacklist = config['blacklist']
        maxValue = config['maxValue']
        blocknativeKey = config['blocknativeKey']
        barkKey = config['barkKey']
        follows = config['follow']
        nameabi = {
            'inputs': [],
            'name': 'name',
            'outputs': [{'internalType': 'string', 'name': '', 'type': 'string'}],
            'stateMutability': 'view',
            'type': 'function'
        }
        w3 = Web3(Web3.HTTPProvider(RPC))
        maxGasPrice = config['maxGasPrice']
        maxGasPrice = w3.toWei(maxGasPrice, 'gwei')
        maxGasLimit = int(config['maxGasLimit'])
        maxValue = w3.toWei(maxValue, 'ether')
        chainId = w3.eth.chainId
        accounts = []
        for privateKey in privateKeys:
            accounts.append(w3.eth.account.privateKeyToAccount(privateKey))
        mintadd = []
        ETHPrice = getETHPrice()
        print_color('ETH单价: ' + str(ETHPrice), 'green')
        methodNameDict = {
            '0xab834bab': {'method': 'atomicMatch_', 'isMint': False},
            '0xa22cb465': {'method': 'setApprovalForAll', 'isMint': False},
            '0x23b872dd': {'method': 'transferFrom', 'isMint': False},
            '0xa8a41c70': {'method': 'cancelOrder_', 'isMint': False}
        }
        main()
    except Exception as e:
        print_color(str(e), 'red')
        time.sleep(10)
