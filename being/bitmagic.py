"""Bit operation helpers. Since integers are immutable most of these do not work
in-place but return a new value instead
"""


def check_bit(value: int, bit: int) -> int:
    """Check n-th bit of value.

    Args:
        value: Number to check.
        bit: Bit number.

    Returns:
        N-th bit value

    Examples:
        >>> check_bit(0b1000, 0)
        0

        >>> bin(check_bit(0b1000, 3))
        '0b1000'
    """
    return value & (1 << bit)


def set_bit(value: int, bit: int) -> int:
    """Set n-th bit of value.

    Args:
        value: Number to set bit.
        bit: Bit number.

    Returns:
        Value with set n-th bit.

    Example:
        >>> bin(set_bit(0b11011, 2))
        '0b11111'
    """
    return value | (1 << bit)


def clear_bit(value: int, bit: int) -> int:
    """Clear n-th bit of value.

    Args:
        value: Number to clear bit.
        bit: Bit number.

    Returns:
        Value with cleared n-th bit

    Example:
        >>> clear_bit(0b1000, 3)
        0
    """
    return value & ~(1 << bit)


def toggle_bit(value: int, bit: int) -> int:
    """Toggle n-th bit of value.

    Args:
        value: Number to toggle bit.
        bit: Bit number.

    Returns:
        Value with toggled n-th bit.
    """
    return value ^ (1 << bit)


def check_bit_mask(value: int, mask: int) -> bool:
    """Check if all bits of mask are set in value.

    Args:
        value: Number to check.
        mask: Bit mask number.

    Returns:
        If mask is set in value.

    Examples:
        >>> check_bit_mask(0b1101, mask=0b1001)
        True

        >>> check_bit_mask(0b0111, mask=0b1001)
        False
    """
    return (value & mask) == mask


def bit_mask(width: int) -> int:
    """All ones bit mask for a given width.

    Args:
        width: Width of bit mask.

    Returns:
        Bit mask.

    Example:
        >>> bin(bit_mask(width=4))
        '0b1111'
    """
    return (2 ** width) - 1
