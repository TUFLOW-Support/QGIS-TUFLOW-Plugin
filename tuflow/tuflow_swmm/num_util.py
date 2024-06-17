import numpy as np


def round_to_n_digits(x, n_figs):
    power = 10 ** np.floor(np.log10(np.abs(x).clip(1e-200)))
    rounded = np.round(x / power, n_figs - 1) * power
    return rounded
