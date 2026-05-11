using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Assets.SingaPort
{
    public class Group
    {
        public int Index { get; set; }
        public int TEUs { get; set; }
        public int Size { get; set; }
        public List<Container> Containers { get; set; } = new List<Container>();
        public DateTime Timestamp_Unstack { get; set; }
        public override string ToString()
        {
            return $"Group#{Index}";
        }
    }

    public enum ContainerSize { FortyFeet, TwentyFeet }
    public class Container
    {
        public static int Count { get; private set; } = 0;
        public const float Height = 2.59f;
        public int Index { get;private set; }
        public ContainerSize Size { get; private set; }
        public Group Group { get; set; }
        public Block Block { get; set; }
        public Slot Slot { get; set; }
        public Container(Group group)
        {
            Index = ++Count;
            Group = group;
            Size = group.TEUs == 2 ? ContainerSize.FortyFeet : ContainerSize.TwentyFeet;
        }
    }

    
}
