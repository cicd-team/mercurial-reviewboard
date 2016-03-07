def splitVersionPart(part):
    for i in xrange(len(part)):
        if not part[i].isdigit():
            if i:
                return (int(part[:i]), part[i:])
            else:
                return (0, part[i:])

    return (int(part), '')

def cmpParts(p1, p2):
    (p1num, p1str) = splitVersionPart(p1)
    (p2num, p2str) = splitVersionPart(p2)
    
    if p1num != p2num:
        return cmp(p1num, p2num)
    else:
        return cmp(p1str, p2str)
    
class HgVersion:
    def __init__(self, versionString):
        self.parts = versionString.split('.')

    def __cmp__(self, other):
        limit = min(len(self.parts), len(other.parts))

        for i in xrange(limit):
            result = cmpParts(self.parts[i], other.parts[i])
            if result:
                return result

        return cmp(len(self.parts), len(other.parts))
