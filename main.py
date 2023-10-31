from data.data import DATA
from data.abi.abi import ABI_MERKLY_REFUEL
from config import MERKLY_CONTRACTS, LAYERZERO_CHAINS_ID
from setting import SLEEP_FROM, SLEEP_TO, RANDOM_WALLETS
from helpers import get_web3, add_gas_price, sign_tx, add_gas_limit_layerzero, check_status_tx, intToDecimal, sleeping, cheker_gwei

from loguru import logger
from web3 import Web3
from sys import stderr
import random
from eth_abi import encode
from termcolor import cprint

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <3}</level> | <level>{message}</level>")

chain_ID_from = {
    '1': 'arbitrum',   '2': 'optimism',  '3': 'bsc',
    '4': 'polygon', '5': 'celo',
}

chain_ID_to = {
    '1': 'base', '2': 'kava',
    '3': 'linea', '4': 'zora', '5': 'scroll', '6': 'conflux'
}


def get_adapterParams(gaslimit: int, amount: int):
    return Web3.to_hex(encode(["uint16", "uint64", "uint256"], [2, gaslimit, amount])[30:])


def merkly_refuel(from_chain, to_chain, amount_from, amount_to, private_key):
    global module_str

    try:

        module_str = f'merkly_refuel : {from_chain} => {to_chain}'
        logger.info(module_str)

        amount = round(random.uniform(amount_from, amount_to), 8)

        web3 = get_web3(from_chain)
        account = web3.eth.account.from_key(private_key)
        wallet = account.address

        contract = web3.eth.contract(address=Web3.to_checksum_address(
            MERKLY_CONTRACTS[from_chain]), abi=ABI_MERKLY_REFUEL)

        value = intToDecimal(amount, 18)
        adapterParams = get_adapterParams(250000, value) + wallet[2:].lower()
        send_value = contract.functions.estimateGasBridgeFee(
            LAYERZERO_CHAINS_ID[to_chain], False, adapterParams).call()

        contract_txn = contract.functions.bridgeGas(
            LAYERZERO_CHAINS_ID[to_chain],
            '0x0000000000000000000000000000000000000000',  # _zroPaymentAddress
            adapterParams
        ).build_transaction(
            {
                "from": wallet,
                "value": send_value[0],
                "nonce": web3.eth.get_transaction_count(wallet),
                'gasPrice': 0,
                'gas': 0,
            }
        )

        if amount > 0:
            if from_chain == 'bsc':
                # специально ставим 1.2 гвей, так транза будет дешевле
                contract_txn['gasPrice'] = 1200000000
            else:
                contract_txn = add_gas_price(web3, contract_txn)

            contract_txn = add_gas_limit_layerzero(web3, contract_txn)

            tx_hash = sign_tx(web3, contract_txn, private_key)
            tx_link = f'{DATA[from_chain]["scan"]}/{tx_hash}'

            status = check_status_tx(from_chain, tx_hash)
            if status == 1:
                logger.success(f'[{wallet}] {module_str} | {tx_link}')
                return "success"

        else:
            logger.error(f"{module_str} : баланс равен 0")

    except Exception as error:
        logger.error(f'{module_str} | {error}')


if __name__ == '__main__':
    while True:
        cprint('Выбери сеть откуда заправляем: ', 'blue')
        print('1. Arbitrum')
        print('2. Optimism')
        print('3. BSC')
        print('4. Polygon')
        print('5. Celo')
        cprint('0. Закончить работу', 'red')
        id_from_chain = input('Номер сети: ')

        if id_from_chain == '0':
            break

        from_chain = chain_ID_from[id_from_chain]

        cprint('Выбери сеть куда заправляем: ', 'blue')
        print('1. Base'),
        print('2. Kava'),
        print('3. Linea')
        print('4. Zora')
        print('5. Scroll')
        print('6. Conflux')

        id_to_chain = input('Номер сети: ')
        to_chain = chain_ID_to[id_to_chain]
        cprint(
            f'Сейчас надо будет ввести минимальное и максимально значение. Пример 0.0001',
            'yellow')

        min_count = float(input('Минимальное количество нативного токена приемника: '))
        max_count = float(input('Максимальное количество нативного токена приемника: '))

        with open("keys.txt", "r") as file:
            keys = [line.strip() for line in file.readlines()]

        if RANDOM_WALLETS:
            random.shuffle(keys)

        for key in keys:
            cheker_gwei()
            merkly_refuel(from_chain, to_chain, min_count, max_count, key)
            sleeping(SLEEP_FROM, SLEEP_TO)

    print("Скрипт закончил работу.")
