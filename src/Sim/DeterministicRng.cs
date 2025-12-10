namespace Terrarium.Sim;

/// <summary>
/// Simple xor-shift128 RNG for deterministic, fast random numbers.
/// </summary>
public sealed class DeterministicRng
{
    private uint _x;
    private uint _y;
    private uint _z;
    private uint _w;

    public DeterministicRng(int seed)
    {
        _x = (uint)seed;
        _y = 362436069;
        _z = 521288629;
        _w = 88675123;
        if (_x == 0)
        {
            _x = 2463534242;
        }
    }

    public int NextInt(int maxExclusive)
    {
        return (int)(NextUInt() % (uint)maxExclusive);
    }

    public float NextFloat()
    {
        return (NextUInt() & 0xFFFFFF) / (float)0x1000000;
    }

    public float NextRange(float min, float max)
    {
        return min + (max - min) * NextFloat();
    }

    public Vec2 NextUnitCircle()
    {
        var angle = NextRange(0, MathF.PI * 2f);
        return new Vec2(MathF.Cos(angle), MathF.Sin(angle));
    }

    private uint NextUInt()
    {
        var t = _x ^ (_x << 11);
        _x = _y;
        _y = _z;
        _z = _w;
        _w = _w ^ (_w >> 19) ^ (t ^ (t >> 8));
        return _w;
    }
}
