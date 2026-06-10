def maybe_pluralise(word: str, count: int):
    """
    Pluralises the word if the count is anything other than 1.

    :param word: Original word (plural form expected to be simply this plus "s").
    :param count: Count.
    :return:
    """
    return word if count == 1 else word + "s"