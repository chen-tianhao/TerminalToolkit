namespace Assets.SingaPort
{
    public class Slot
    {
        public int Bay { get; set; }
        public int Row { get; set; }
        public int Tier { get; set; }

        public Slot(int bay, int row, int tier)
        {
            this.Bay = bay;
            this.Row = row;
            this.Tier = tier;
        }

        public override bool Equals(object? obj)
        {
            if (obj is Slot other)
                return Bay == other.Bay && Row == other.Row && Tier == other.Tier;
            return false;
        }

        public override int GetHashCode()
        {
            return HashCode.Combine(Bay, Row, Tier);
        }

        public override string ToString()
        {
            return $"Slot({Bay},{Row},{Tier})";
        }
    }
}