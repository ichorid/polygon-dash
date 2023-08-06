from pynng import Pair0
import pynng

url = 'tcp://127.0.0.1:54321'

REQUEST_POP_TRANSACTIONS = "pop_transactions"

#with Pair0(listen='tcp://127.0.0.1:54321') as s1, \
#        Pair0(dial='tcp://127.0.0.1:54321') as s2:

if __name__ == "__main__":
    #with Pair0(listen='tcp://127.0.0.1:54321') as s1:
    #    s1.send(b'Well hello there')
    #    print(s1.recv())
    with pynng.Req0() as sock:
        sock.dial(url)
        print(f"NODE1: SENDING DATE REQUEST")
        sock.send(REQUEST_POP_TRANSACTIONS.encode())
        msg = sock.recv_msg()
        print(f"NODE1: RECEIVED DATE {msg.bytes.decode()}")
