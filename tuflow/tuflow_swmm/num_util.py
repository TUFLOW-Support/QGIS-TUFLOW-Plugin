import numpy as np


def round_to_n_digits(x, n_figs):
    power = 10 ** np.floor(np.log10(np.abs(x).clip(1e-200)))
    rounded = np.round(x / power, n_figs - 1) * power
    return rounded


def ceiling_to_n_digits(x, n_figs):
    power = 10 ** n_figs
    return np.ceil(x / power) * power


def floor_to_n_digits(x, n_figs):
    power = 10 ** n_figs
    return np.floor(x / power) * power
