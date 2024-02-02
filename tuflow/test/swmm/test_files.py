import os


def get_input_full_filenames(filenames):
    dir = os.path.dirname(__file__)

    return [os.path.join(dir, "input", x) for x in filenames]


def get_output_path(filename):
    dir = os.path.dirname(__file__)
    return os.path.join(dir, "output", filename)


def get_compare_path(filename):
    dir = os.path.dirname(__file__)
    return os.path.join(dir, "compare", filename)
