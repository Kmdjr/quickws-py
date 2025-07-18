
def clamp(value: int | float, min: int | float = 0, max: int | float = float("inf")) -> float:
    """
    Clamp the input `value` between `min` and `max` (inclusive) and return the result.

    Args:
        value (int | float): Input value to clamp.
        min (int | float): Minimum allowed value.
        max (int | float): Maximum allowed value.

    Returns:
        float: Clamped value.
    """
    if not all(isinstance(i, (int, float)) for i in [value, min, max]):
        raise ValueError(f"Invalid numeric inputs: value={value}, min={min}, max={max}")
    return max if value > max else min if value < min else value

def hle(val: int | float, test_against: int | float) -> int:
    """Compare `val` to `test_against`. Returns 1 if higher, 0 if lower, 2 if equal."""
    if val > test_against:
        return 1
    elif val < test_against:
        return 0
    return 2
