"""
    Miscellaneous support functions
"""


def round_away(val):
    """Round away from zero"""
    val += -0.5 if val < 0 else 0.5
    return int(val)
