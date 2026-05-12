class Slot:
    """槽位三维坐标 (Bay, Row, Tier)。"""

    __slots__ = ('bay', 'row', 'tier')

    def __init__(self, bay: int, row: int, tier: int):
        self.bay = bay
        self.row = row
        self.tier = tier

    def __repr__(self) -> str:
        return f"Slot(Bay={self.bay}, Row={self.row}, Tier={self.tier})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Slot):
            return False
        return self.bay == other.bay and self.row == other.row and self.tier == other.tier

    def __hash__(self) -> int:
        return hash((self.bay, self.row, self.tier))
