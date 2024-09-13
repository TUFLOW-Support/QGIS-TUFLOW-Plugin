import os


def get_input_full_filenames(filenames):
    root_dir = os.path.dirname(__file__)

    return [os.path.join(root_dir, "input", x) for x in filenames]


def get_input_path(filename):
    root_dir = os.path.dirname(__file__)
    return os.path.join(root_dir, "input", filename)


def get_output_path(filename):
    root_dir = os.path.dirname(__file__)
    return os.path.join(root_dir, "output", filename)


def get_compare_path(filename):
    root_dir = os.path.dirname(__file__)
    return os.path.join(root_dir, "compare", filename)

