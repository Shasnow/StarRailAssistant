using System;
using System.Collections.Generic;

namespace SRAFrontend.utilities;
public class Version:IComparable<Version>
{
    private readonly int _major;
    private readonly int _minor;
    private readonly int _patch;
    private readonly int _preRelease;
    private readonly int _preReleasePatch;

    public Version(string versionString)
    {
        var mainAndPre = versionString.TrimStart('v').Split('-');
        var mainParts = mainAndPre[0].Split('.');
        _major = int.Parse(mainParts[0]);
        _minor = int.Parse(mainParts[1]);
        _patch = int.Parse(mainParts[2]);
        if (mainAndPre.Length > 1)
        {
            var preParts = mainAndPre[1].Split('.');
            _preRelease = preParts[0] switch
            {
                "alpha" => 1,
                "beta" => 2,
                "rc" => 3,
                _ => 4
            };
            _preReleasePatch = preParts.Length > 1 ? int.Parse(preParts[1]) : 0;
        }
        else
        {
            _preRelease = 4; // No pre-release
            _preReleasePatch = 0;
        }
    }

    public int CompareTo(Version? other)
    {
        if (other == null) return 1;

        if (_major != other._major)
            return _major.CompareTo(other._major);
        if (_minor != other._minor)
            return _minor.CompareTo(other._minor);
        if (_patch != other._patch)
            return _patch.CompareTo(other._patch);
        if (_preRelease != other._preRelease)
            return _preRelease.CompareTo(other._preRelease);
        return _preReleasePatch.CompareTo(other._preReleasePatch);
    }

    public override string ToString()
    {
        return $"{_major}.{_minor}.{_patch}-{_preRelease}.{_preReleasePatch}";
    }

    public static bool operator <(Version? left, Version? right)
    {
        return Comparer<Version>.Default.Compare(left, right) < 0;
    }

    public static bool operator >(Version? left, Version? right)
    {
        return Comparer<Version>.Default.Compare(left, right) > 0;
    }

    public static bool operator <=(Version? left, Version? right)
    {
        return Comparer<Version>.Default.Compare(left, right) <= 0;
    }

    public static bool operator >=(Version? left, Version? right)
    {
        return Comparer<Version>.Default.Compare(left, right) >= 0;
    }
}