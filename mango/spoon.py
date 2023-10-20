import itertools
import numpy as np

def process_field(field, delimiter, lower=False, pattern=None):
    if isinstance(field, str):
        field = [field]
    if delimiter is not None:
        field = set(
            map(
                lambda x: x.strip(), itertools.chain.from_iterable(
                    [item.lower().split(delimiter) if lower else item.split(delimiter) for item in field if isinstance(item, str)]
                    )
                )
            )
    
    return np.array(list(field))
