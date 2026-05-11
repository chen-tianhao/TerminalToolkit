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
    }
}