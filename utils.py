import random

def derangement(elements):
    for _ in range(1000):
        shuffled = elements[:]
        random.shuffle(shuffled)
        if all(e != s for e, s in zip(elements, shuffled)):
            return shuffled
    return None
