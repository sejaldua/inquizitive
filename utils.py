def truncate_text(text_input: str, max_length: int = 50) -> str:
    """
    Truncate a text to a specified maximum length, adding ellipsis if truncated.
    :param text_input: The input text.
    :param max_length: The maximum allowed length for the output text.
    :return:
    """
    if len(text_input) > max_length:
        return text_input[:max_length] + "..."
    else:
        return text_input