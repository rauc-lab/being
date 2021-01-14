"""Bit operation helpers."""


def check_bit(value: int, bit: int) -> int:
    """Check n-th bit of value."""
    return value & (1 << bit)


def set_bit(value: int, bit: int) -> int:
    """Set n-th bit of value."""
    return value | (1 << bit)


def clear_bit(value: int, bit: int) -> int:
    """Clear n-th bit of value."""
    return value & ~(1 << bit)


def toggle_bit(value: int, bit: int) -> int:
    """Toggle n-th bit of value."""
    return value ^ (1 << bit)


def check_bit_mask(value: int, mask: int) -> bool:
    """Check if all bits of mask are set in value.

    Usage:
        >>> check_bit_mask(0b1101, mask=0b1001)
        True

        >>> check_bit_mask(0b0111, mask=0b1001)
        False
    """
    return (value & mask) == mask
