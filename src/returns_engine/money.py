"""Exact financial primitives; eligibility/refund policy is implemented later."""

from decimal import Decimal, ROUND_HALF_UP


def minor_units(amount: str | Decimal) -> int:
    if not isinstance(amount, (str, Decimal)):
        raise TypeError("Use Decimal or decimal string, never float")
    value = Decimal(amount)
    if not value.is_finite() or value < 0:
        raise ValueError("Money must be finite and nonnegative")
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def allocate_minor(total: int, quantity: int) -> tuple[int, ...]:
    if type(total) is not int or total < 0 or type(quantity) is not int or quantity <= 0:
        raise ValueError("Nonnegative integer total and positive integer quantity required")
    quotient, remainder = divmod(total, quantity)
    return tuple(quotient + (i < remainder) for i in range(quantity))


def basis_points(amount: int, rate: int) -> int:
    """Nonnegative integer HALF_UP rounding, without binary floating point."""
    if type(amount) is not int or amount < 0 or type(rate) is not int or not 0 <= rate <= 10000:
        raise ValueError("Integer amount >=0 and rate 0..10000 required")
    return (amount * rate + 5000) // 10000


def allocate_proportional(total: int, weights: list[int]) -> list[int]:
    """Largest remainder; ties resolved by stable input position."""
    if type(total) is not int or total < 0 or not weights or any(type(w) is not int or w < 0 for w in weights):
        raise ValueError("Nonnegative integer total and nonempty integer weights required")
    denominator=sum(weights)
    if not denominator:
        if total: raise ValueError("Cannot allocate positive amount to zero weights")
        return [0]*len(weights)
    shares=[total*w//denominator for w in weights]
    order=sorted(range(len(weights)),key=lambda i: (-(total*weights[i] % denominator),i))
    for i in order[:total-sum(shares)]: shares[i]+=1
    return shares


def unit_paid(line):
    discounts=allocate_minor(line["line_discount_minor"]+line["order_discount_allocated_minor"],line["quantity"])
    taxes=allocate_minor(line["tax_minor"],line["quantity"])
    return tuple(line["unit_price_minor"]-discounts[i]+taxes[i] for i in range(line["quantity"]))
