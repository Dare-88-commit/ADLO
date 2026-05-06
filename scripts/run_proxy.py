"""Print a concise ADLO market summary in the terminal."""
from __future__ import annotations

from adlo.service import load_market_series, market_dashboard


def main() -> None:
    markets = load_market_series()
    for name, series in markets.items():
        package = market_dashboard(series, desired_size=100)
        selected = package["selected"]
        advice = package["advice"]
        stress = "n/a" if selected["liquidity_stress"] is None else f"{selected['liquidity_stress']:.2f}"
        window_score = (
            "n/a" if selected["issuance_window_score"] is None else f"{selected['issuance_window_score']:.0f}"
        )
        hole_probability = (
            "n/a"
            if selected["liquidity_hole_probability"] is None
            else f"{selected['liquidity_hole_probability']:.0f}"
        )
        print(
            f"{name} | {selected['latest_date']} | "
            f"stance={selected['stance']} | "
            f"stress={stress}"
        )
        print(
            f"  window_score={window_score} | "
            f"hole_probability={hole_probability}% | "
            f"executable_now={advice['executable_now']}"
        )
        print(f"  {selected['headline']}")


if __name__ == "__main__":
    main()
