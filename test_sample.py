# Sample code with intentional design and style issues to test the reviewer.
import time

x = 10
GLOBAL_LST = []

def process_data(data):
    # This function is too long, uses poor names, has high nesting, and lacks docstrings.
    global GLOBAL_LST
    res = []
    if data is not None:
        for item in data:
            if 'val' in item:
                v = item['val']
                if v > 0:
                    for i in range(v):
                        temp = v * i
                        if temp % 2 == 0:
                            # print(temp)
                            res.append(temp)
                        else:
                            # do nothing
                            pass
            else:
                print("invalid key")
    
    # Inefficient list operation
    for r in res:
        if r not in GLOBAL_LST:
            GLOBAL_LST.append(r)
            
    return res

def calculate(a, b, op):
    if op == 'add':
        return a + b
    elif op == 'sub':
        return a - b
    elif op == 'mul':
        return a * b
    elif op == 'div':
        if b != 0:
            return a / b
        else:
            return None
    else:
        return None

class user:
    def __init__(self, n, a):
        self.n = n
        self.a = a

    def show(self):
        print(self.n, self.a)
