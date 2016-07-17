import random
from collections import defaultdict
from hashlib import md5


def md5hash(filename):
    f = open(filename, 'r+b')
    data = f.read()
    f.close()
    return md5(data).hexdigest()


def int2bytes(value, length=2, reverse=True):
    # reverse=True means high-order byte first
    bs = []
    while value:
        bs.append(value & 255)
        value = value >> 8

    while len(bs) < length:
        bs.append(0)

    if not reverse:
        bs = reversed(bs)

    return bs[:length]


def read_multi(f, length=2, reverse=True):
    vals = map(ord, f.read(length))
    if reverse:
        vals = list(reversed(vals))
    value = 0
    for val in vals:
        value = value << 8
        value = value | val
    return value


def write_multi(f, value, length=2, reverse=True):
    vals = []
    while value:
        vals.append(value & 0xFF)
        value = value >> 8
    if len(vals) > length:
        raise Exception("Value length mismatch.")

    while len(vals) < length:
        vals.append(0x00)

    if not reverse:
        vals = reversed(vals)

    f.write(''.join(map(chr, vals)))


utilrandom = random.Random()
utran = utilrandom
random = utilrandom


def mutate_bits(value, size=8, odds_multiplier=2.0):
    bits_set = bin(value).count('1')
    bits_unset = size - bits_set
    assert bits_unset >= 0
    lowvalue = min(bits_set, bits_unset)
    lowvalue = max(lowvalue, 1)
    multiplied = int(round(size * odds_multiplier))
    for i in range(size):
        if random.randint(1, multiplied) <= lowvalue:
            value ^= (1 << i)
    return value


def shuffle_bits(value, size=8, odds_multiplier=None):
    numbits = bin(value).count("1")
    if numbits:
        digits = random.sample(range(size), numbits)
        newvalue = 0
        for d in digits:
            newvalue |= (1 << d)
        value = newvalue
    if odds_multiplier is not None:
        value = mutate_bits(value, size, odds_multiplier)
    return value


BOOST_AMOUNT = 2.0


def mutate_normal(value, minimum=0, maximum=0xFF,
                  reverse=False, smart=True, chain=True, return_float=False):
    value = max(minimum, min(value, maximum))
    rev = reverse
    if smart:
        if value > (minimum + maximum) / 2:
            rev = True
        else:
            rev = False

    if rev:
        value = maximum - value
    else:
        value = value - minimum

    BOOST_FLAG = False
    if value < BOOST_AMOUNT:
        value += BOOST_AMOUNT
        if value > 0:
            BOOST_FLAG = True
        else:
            value = 0

    if value > 0:
        half = value / 2.0
        a, b = random.random(), random.random()
        value = half + (half * a) + (half * b)

    if BOOST_FLAG:
        value -= BOOST_AMOUNT

    if rev:
        value = maximum - value
    else:
        value = value + minimum

    if chain and random.randint(1, 10) == 10:
        return mutate_normal(value, minimum=minimum, maximum=maximum,
                             reverse=reverse, smart=smart, chain=True)
    else:
        value = max(minimum, min(value, maximum))
        if not return_float:
            value = int(round(value))
        return value


def mutate_index(index, length, continuation=None,
                 basic_range=None, extended_range=None):
    if length == 0:
        return None

    highest = length - 1
    continuation = continuation or [True, False]
    basic_range = basic_range or (-3, 3)
    extended_range = extended_range or (-1, 1)

    index += utran.randint(*basic_range)
    index = max(0, min(index, highest))
    while utran.choice(continuation):
        index += utran.randint(*extended_range)
        index = max(0, min(index, highest))

    return index


def line_wrap(things, width=16):
    newthings = []
    while things:
        newthings.append(things[:width])
        things = things[width:]
    return newthings


def hexstring(value):
    if type(value) is str:
        value = "".join(["{0:0>2}".format("%x" % ord(c)) for c in value])
    elif type(value) is int:
        value = "{0:0>2}".format("%x" % value)
    elif type(value) is list:
        value = " ".join([hexstring(v) for v in value])
    return value


generator = {}


def generate_name(size=None, maxsize=10, namegen_table=None):
    if namegen_table is not None or not generator:
        lookback = None
        for line in open(namegen_table):
            key, values = tuple(line.strip().split())
            generator[key] = values
            if not lookback:
                lookback = len(key)
        return

    lookback = len(generator.keys()[0])

    if not size:
        halfmax = maxsize / 2
        size = random.randint(1, halfmax) + random.randint(1, halfmax)
        if size < 4:
            size += random.randint(0, halfmax)

    def has_vowel(text):
        for c in text:
            if c.lower() in "aeiouy":
                return True
        return False

    while True:
        starts = sorted([s for s in generator if s[0].isupper()])
        name = random.choice(starts)
        name = name[:size]
        while len(name) < size:
            key = name[-lookback:]
            if key not in generator and size - len(name) < len(key):
                name = random.choice(starts)
                continue
            if key not in generator or (random.randint(1, 15) == 15
                                        and has_vowel(name[-2:])):
                if len(name) <= size - lookback:
                    if len(name) + len(key) < maxsize:
                        name += " "
                    name += random.choice(starts)
                    continue
                else:
                    name = random.choice(starts)
                    continue

            c = random.choice(generator[key])
            name = name + c

        if len(name) >= size:
            return name


def get_snes_palette_transformer(use_luma=False, always=None, middle=True,
                                 basepalette=None):
    def generate_swapfunc(swapcode=None):
        if swapcode is None:
            swapcode = utran.randint(0, 7)

        f = lambda w: w
        g = lambda w: w
        h = lambda w: w
        if swapcode & 1:
            f = lambda (x, y, z): (y, x, z)
        if swapcode & 2:
            g = lambda (x, y, z): (z, y, x)
        if swapcode & 4:
            h = lambda (x, y, z): (x, z, y)
        swapfunc = lambda w: f(g(h(w)))

        return swapfunc

    def shift_middle(triple, degree, ungray=False):
        low, medium, high = tuple(sorted(triple))
        triple = list(triple)
        mediumdex = triple.index(medium)
        if ungray:
            lowdex, highdex = triple.index(low), triple.index(high)
            while utran.choice([True, False]):
                low -= 1
                high += 1

            low = max(0, low)
            high = min(31, high)

            triple[lowdex] = low
            triple[highdex] = high

        if degree < 0:
            value = low
        else:
            value = high
        degree = abs(degree)
        a = (1 - (degree/90.0)) * medium
        b = (degree/90.0) * value
        medium = a + b
        medium = int(round(medium))
        triple[mediumdex] = medium
        return tuple(triple)

    def get_ratio(a, b):
        if a > 0 and b > 0:
            return max(a, b) / float(min(a, b))
        elif abs(a-b) <= 1:
            return 1.0
        else:
            return 9999

    def color_to_components(color):
        blue = (color & 0x7c00) >> 10
        green = (color & 0x03e0) >> 5
        red = color & 0x001f
        return (red, green, blue)

    def components_to_color((red, green, blue)):
        return red | (green << 5) | (blue << 10)

    if always is not None and basepalette is not None:
        raise Exception("'always' argument incompatible with 'basepalette'")

    swapmap = {}
    if basepalette is not None and not use_luma:
        threshold = 1.2

        def color_to_index(color):
            red, green, blue = color_to_components(color)
            a = red >= green
            b = red >= blue
            c = green >= blue
            d = get_ratio(red, green) >= threshold
            e = get_ratio(red, blue) >= threshold
            f = get_ratio(green, blue) >= threshold

            index = (d << 2) | (e << 1) | f
            index |= ((a and not d) << 5)
            index |= ((b and not e) << 4)
            index |= ((c and not f) << 3)

            return index

        colordict = defaultdict(set)
        for color in basepalette:
            index = color_to_index(color)
            colordict[index].add(color)

        saturated = dict((k, v) for (k, v) in colordict.items() if k & 0x7)
        satlist = sorted(saturated)
        random.shuffle(satlist)
        grouporder = sorted(satlist, key=lambda k: len(saturated[k]),
                            reverse=True)
        if grouporder:
            dominant = grouporder[0]
            domhue, domsat = dominant >> 3, dominant & 0x7
            for key in grouporder[1:]:
                colhue, colsat = key >> 3, key & 0x7
                if (domhue ^ colhue) & (domsat | colsat) == 0:
                    continue
                secondary = key
                break
            else:
                secondary = dominant
            sechue, secsat = secondary >> 3, secondary & 0x7
        else:
            dominant, domhue, domsat = 0, 0, 0
            secondary, sechue, secsat = 0, 0, 0

        while True:
            domswap = random.randint(0, 7)
            secswap = random.randint(0, 7)
            tertswap = random.randint(0, 7)
            if domswap == secswap:
                continue
            break

        for key in colordict:
            colhue, colsat = key >> 3, key & 0x7
            if ((domhue ^ colhue) & (domsat | colsat)) == 0:
                if ((sechue ^ colhue) & (secsat | colsat)) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & (secsat | colsat)) == 0:
                swapmap[key] = secswap
            elif ((domhue ^ colhue) & domsat) == 0:
                if ((sechue ^ colhue) & secsat) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & secsat) == 0:
                swapmap[key] = secswap
            elif ((domhue ^ colhue) & colsat) == 0:
                if ((sechue ^ colhue) & colsat) == 0:
                    swapmap[key] = random.choice([domswap, secswap])
                else:
                    swapmap[key] = domswap
            elif ((sechue ^ colhue) & colsat) == 0:
                swapmap[key] = secswap
            else:
                swapmap[key] = tertswap

    elif basepalette is not None and use_luma:
        def color_to_index(color):
            red, green, blue = color_to_components(color)
            index = red + green + blue
            return index

        values = []
        for color in basepalette:
            index = color_to_index(color)
            values.append(index)
        values = sorted(values)
        low, high = min(values), max(values)
        median = values[len(values)/2]
        clusters = [set([low]), set([high])]
        done = set([low, high])
        if median not in done and random.choice([True, False]):
            clusters.append(set([median]))
            done.add(median)

        to_cluster = sorted(basepalette)
        random.shuffle(to_cluster)
        for color in to_cluster:
            index = color_to_index(color)
            if index in done:
                continue
            done.add(index)

            def cluster_distance(cluster):
                distances = [abs(index-i) for i in cluster]
                return sum(distances) / len(distances)
                nearest = min(cluster, key=lambda x: abs(x-index))
                return abs(nearest-index)

            chosen = min(clusters, key=cluster_distance)
            chosen.add(index)

        swapmap = {}
        for cluster in clusters:
            swapcode = random.randint(0, 7)
            for index in cluster:
                try:
                    assert index not in swapmap
                except:
                    import pdb; pdb.set_trace()
                swapmap[index] = swapcode

        remaining = [i for i in xrange(94) if i not in swapmap.keys()]
        random.shuffle(remaining)

        def get_nearest_swapcode(index):
            nearest = min(swapmap, key=lambda x: abs(x-index))
            return nearest

        for i in remaining:
            nearest = get_nearest_swapcode(i)
            swapmap[i] = swapmap[nearest]

    else:
        def color_to_index(color):
            return 0

        if always:
            swapmap[0] = random.randint(1, 7)
        else:
            swapmap[0] = random.randint(0, 7)

    for key in swapmap:
        swapmap[key] = generate_swapfunc(swapmap[key])

    if middle:
        degree = utran.randint(-75, 75)

    def palette_transformer(raw_palette, single_bytes=False):
        if single_bytes:
            raw_palette = zip(raw_palette, raw_palette[1:])
            raw_palette = [p for (i, p) in enumerate(raw_palette) if not i % 2]
            raw_palette = [(b << 8) | a for (a, b) in raw_palette]
        transformed = []
        for color in raw_palette:
            index = color_to_index(color)
            swapfunc = swapmap[index]
            red, green, blue = color_to_components(color)
            red, green, blue = swapfunc((red, green, blue))
            if middle:
                red, green, blue = shift_middle((red, green, blue), degree)
            color = components_to_color((red, green, blue))
            transformed.append(color)
        if single_bytes:
            major = [p >> 8 for p in transformed]
            minor = [p & 0xFF for p in transformed]
            transformed = []
            for a, b in zip(minor, major):
                transformed.append(a)
                transformed.append(b)
        return transformed

    return palette_transformer


def rewrite_snes_title(text, filename, version):
    f = open(filename, 'r+b')
    while len(text) < 20:
        text += ' '
    if len(text) > 20:
        text = text[:19] + "?"
    f.seek(0xFFC0)
    f.write(text)
    f.seek(0xFFDB)
    f.write(chr(int(version)))
    f.close()


def rewrite_snes_checksum(filename, megabits=24):
    MEGABIT = 0x20000
    f = open(filename, 'r+b')
    subsums = [sum(map(ord, f.read(MEGABIT))) for _ in xrange(megabits)]
    if megabits % 16 != 0:
        subsums += subsums[-8:]
    checksum = sum(subsums) & 0xFFFF
    f.seek(0xFFDE)
    write_multi(f, checksum, length=2)
    f.seek(0xFFDC)
    write_multi(f, checksum ^ 0xFFFF, length=2)
    f.close()


class classproperty(property):
    def __get__(self, inst, cls):
        return self.fget(cls)
