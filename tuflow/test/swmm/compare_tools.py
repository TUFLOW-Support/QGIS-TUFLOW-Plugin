import re

def process_floats(text):
    """
    Finds floating-point numbers (with or without leading digits before the decimal)
    in the given text. If a number has at least 5 digits after the decimal, removes
    the last digit from that number.
    """
    # Pattern explanation:
    # (?<!\w)   → ensures the match is not preceded by a letter/number/underscore
    # \d*       → optional digits before decimal
    # \.        → decimal point
    # \d+       → one or more digits after decimal
    # (?!\w)    → ensures the match is not followed by a letter/number/underscore
    pattern = re.compile(r'(?<!\w)\d*\.\d+(?!\w)')

    def modify(match):
        num_str = match.group()
        integer_part, decimal_part = num_str.split('.')
        if len(decimal_part) >= 5:
            decimal_part = decimal_part[:-1]  # remove last digit
        return f"{integer_part}.{decimal_part}"

    return pattern.sub(modify, text)


if __name__ == "__main__":
    # Example usage
    sample_text = "Values: 123.45678, 45.67, .876543, and 100.12345, also .1234."
    result = process_floats(sample_text)

    print("Original:", sample_text)
    print("Processed:", result)
