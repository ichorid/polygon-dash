from datetime import datetime

import pynng

from collector.__main__ import REQUEST_POP_TRANSACTIONS

url = 'tcp://127.0.0.1:54321'

if __name__ == "__main__":
    with pynng.Rep0() as sock:
        sock.listen(url)
        while True:
            msg = sock.recv_msg()
            content = msg.bytes.decode()
            if content == REQUEST_POP_TRANSACTIONS:
                print("NODE0: RECEIVED DATE REQUEST")
                date = str(datetime.now())
                sock.send(date.encode())



