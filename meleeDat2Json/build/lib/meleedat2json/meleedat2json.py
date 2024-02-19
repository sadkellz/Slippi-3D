import argparse
from collections import OrderedDict as odict
import json
import os
import re
import sys
import struct
import time

# Sources:
# https://smashboards.com/threads/melee-dat-format.292603/
# http://opensa.dantarion.com/wiki/Moveset_File_Format_(Melee)
# https://github.com/Adjective-Object/melee_subaction_unpacker

from .events import parseEvents
from .attributes import attributesList


def figatreeShortname(name):
    m = re.match(b".*ACTION_(.*?)_figatree", name)
    if m:
        return m.group(1)
    else:
        return name


class FtDataSubaction(object):
    def __init__(self, datFile, offset):
        values = struct.unpack_from(">4IHHI", datFile.data, offset)
        self.nameOffset = values[0]
        self.animationOffset = values[1]  # Offset to the animation .dat in PlxxAJ
        self.animationSize = values[2]  # Length of that animation .dat
        self.eventsOffset = values[3]
        self.posFlags = values[4]  # related to changing position
        self.characterId = values[5]
        # last 4 bytes are always 00000000; game inserts pointer here to animation in ARAM

        self.name = datFile.getDataString(self.nameOffset)
        self.shortName = figatreeShortname(self.name)

        self.events = parseEvents(datFile.data, self.eventsOffset)

        if datFile.animFileData and self.animationSize > 0:
            # this is just for caching, because we might write exactly this buffer later
            self.animationData = datFile.animFileData[self.animationOffset:self.animationOffset + self.animationSize]
            self.animation = DatFile(self.animationData)
        else:
            self.animation = None


class FtData(object):
    def __init__(self, datFile, offset):
        # header
        values = struct.unpack_from(">6I", datFile.data, offset)
        print(values)
        self.attributesOffset = values[0]
        self.attributesEnd = values[1]
        self.unknown1 = values[2]
        self.subactionsOffset = values[3]
        self.unknown2 = values[4]
        self.subactionsEnd = values[5]

        # load attributes
        attributeDataSize = self.attributesEnd - self.attributesOffset
        print(attributeDataSize)
        fmt = ">"
        for attr in attributesList:
            fmt += attr[0]
        assert attributeDataSize >= struct.calcsize(fmt)  # usually ==, but > for Kirby and Peach
        values = struct.unpack_from(fmt, datFile.data, self.attributesOffset)

        self.attributes = []
        for i, attr in enumerate(attributesList):
            self.attributes.append((attr[1], values[i]))

        # load subactions
        subactionDataSize = self.subactionsEnd - self.subactionsOffset
        subactionCount = subactionDataSize // 24
        assert subactionCount * 24 == subactionDataSize
        self.subactions = []
        self.subroutines = {}
        for i in range(subactionCount):
            start = self.subactionsOffset + i * 24
            subaction = FtDataSubaction(datFile, start)
            self.subactions.append(subaction)

            # we might end up parsing some evnets multiple times here, be we don't care
            for event in subaction.events:
                if event.name == "subroutine" or event.name == "goto":
                    offset = int(event.fields["location"])
                    subroutine = parseEvents(datFile.data, offset)

                    # truncate the goto subroutine at the first "return", otherwise we might have some
                    # subroutine-parts in the JSON multiple times

                    if event.name == "goto":
                        firstReturn = None
                        for i, subEvent in enumerate(subroutine):
                            if subEvent.name == "return":
                                firstReturn = i
                                break

                        assert firstReturn, "'goto {}' from {} did not end in return!".format(offset, subaction.name)
                        subroutine = subroutine[:firstReturn + 1]  # +1 to include the return

                    self.subroutines[offset] = subroutine


# https://smashboards.com/threads/melee-dat-format.292603/page-6#post-20386112
# https://smashboards.com/threads/melee-animation-model-workshop.433432/
class FigaTree(object):
    def __init__(self, datFile, offset):
        # header
        values = struct.unpack_from(">2If2I", datFile.data, offset)
        # 0 for Mario's "Appeal" and Yoshi's "AttackAir*" and "LandingLag*", 1 otherwise
        self.unknown1 = values[0]
        # seems to be always 0
        self.unknown2 = values[1]
        self.numFrames = values[2]
        self.boneTableOffset = values[3]
        self.animDataOffset = values[4]


class ShareJoint(object):

    def __init__(self, datFile, offset):
        # header
        values = struct.unpack_from(">5I9f2I", datFile.data, offset)
        self.name_pointer = values[0]
        self.joint_flags = hex(values[1])
        self.child = values[2]
        self.next_sibling = values[3]
        self.display_object = values[4]
        self.rotation_x = values[5]
        self.rotation_y = values[6]
        self.rotation_z = values[7]
        self.scale_x = values[8]
        self.scale_y = values[9]
        self.scale_z = values[10]
        self.translation_x = values[11]
        self.translation_y = values[12]
        self.translation_z = values[13]
        self.inverse_matrix = values[14]
        self.ref_object = values[15]


class RootNode(object):
    skeleton = []

    def __init__(self, datFile, offset):
        # offset is a offset in fileData!
        values = struct.unpack_from(">2I", datFile.fileData, offset)
        self.rootOffset = values[0]
        self.stringTableOffset = values[1]
        self.name = datFile.getString(self.stringTableOffset)
        self.data = None

        if self.name.startswith(b"ftData"):
            # character data
            self.data = FtData(datFile, self.rootOffset)
        elif self.name.endswith(b"_figatree"):
            # animation file
            self.data = FigaTree(datFile, self.rootOffset)
            self.shortName = figatreeShortname(self.name)
        elif self.name.endswith(b"_Share_joint"):
            # joint data
            self.data = ShareJoint(datFile, self.rootOffset)
            self.skeleton += [self.data.__dict__]
            print(self.traverse(self.data, datFile))
        else:
            print("Warning! Unknown/Unimplemented node type:", self.name)

    def traverse(self, node, datFile):
        if node is None:
            return 0
        count = 1
        if node.child != 0:
            child_node = ShareJoint(datFile, node.child)
            self.skeleton += [child_node.__dict__]
            count += self.traverse(child_node, datFile)

        if node.next_sibling != 0:
            sibling_node = ShareJoint(datFile, node.next_sibling)
            self.skeleton += [sibling_node.__dict__]
            count += self.traverse(sibling_node, datFile)
        return count


class DatFile(object):
    def __init__(self, fileData, animFileData=None):
        # header
        values = struct.unpack_from('>8I', fileData, 0)
        self.fileSize = values[0]
        self.dataBlockSize = values[1]
        self.relocationTableCount = values[2]
        self.rootCount = values[3]
        self.rootCount2 = values[4]
        self.unknown1 = values[5]
        self.unknown2 = values[6]
        self.unknown3 = values[7]

        self.dataBlockOffset = 0x20
        self.relocationTableOffset = self.dataBlockOffset + self.dataBlockSize
        self.relocationTableSize = self.relocationTableCount * 4  # each entry is a uint32
        self.rootNodesOffset = self.relocationTableOffset + self.relocationTableSize
        self.rootNodesSize = (self.rootCount + self.rootCount2) * 8  # each entry is 2*uint32
        self.stringTableOffset = self.rootNodesOffset + self.rootNodesSize

        self.fileData = fileData
        self.data = fileData[self.dataBlockOffset:self.dataBlockOffset + self.dataBlockSize]
        self.animFileData = animFileData

        # load relocation table
        self.relocationTable = list(struct.unpack_from(
            ">{}I".format(self.relocationTableCount),
            fileData, self.relocationTableOffset))

        # load root nodes
        self.rootNodes = []
        for i in range(self.rootCount + self.rootCount2):
            # rootNodesOffset is a offset in fileData!
            node = RootNode(self, self.rootNodesOffset + 0x08 * i)
            self.rootNodes.append(node)

    def getString(self, offset):
        start = self.stringTableOffset + offset
        end = self.fileData.index(b'\0', start)
        return self.fileData[start:end]

    def getDataString(self, offset):
        end = self.data.index(b'\0', offset)
        return self.data[offset:end]

    def toJsonDict(self):
        file_json = odict()
        file_json["nodes"] = []
        for node in self.rootNodes:
            node_json = odict([
                ("name", node.name.decode("utf-8")),
                ("rootOffset", node.rootOffset)
            ])
            if isinstance(node.data, FtData):
                attributes_json = []
                for attr in node.data.attributes:
                    attributes_json.append(odict([
                        ("name", attr[0]),
                        ("value", attr[1]),
                    ]))

                subactions_json = []
                for i, subaction in enumerate(node.data.subactions):
                    subaction_json = odict([
                        ("shortName", subaction.shortName.decode("utf-8")),
                        ("name", subaction.name.decode("utf-8")),
                        ("animOffset", subaction.animationOffset),
                        ("animSize", subaction.animationSize),
                    ])

                    if subaction.animation:
                        if not "animationFiles" in file_json:
                            file_json["animationFiles"] = []
                        subaction_json["animationFile"] = len(file_json["animationFiles"])
                        file_json["animationFiles"].append(subaction.animation.toJsonDict())

                    subaction_json["eventsOffset"] = subaction.eventsOffset
                    subaction_json["events"] = []
                    for event in subaction.events:
                        subaction_json["events"].append(event.toJsonDict())

                    subactions_json.append(subaction_json)

                subroutines_json = odict()
                for offset, subroutine in node.data.subroutines.items():
                    subroutines_json[offset] = []
                    for event in subroutine:
                        subroutines_json[offset].append(event.toJsonDict())

                node_json["data"] = odict([
                    ("attributesOffset", node.data.attributesOffset),
                    ("attributes", attributes_json),
                    ("subactionsOffset", node.data.subactionsOffset),
                    ("subactions", subactions_json),
                    ("subroutines", subroutines_json),
                ])
            elif isinstance(node.data, FigaTree):
                node_json["shortName"] = node.shortName.decode("utf-8")
                node_json.move_to_end("shortName", last=False)
                node_json["data"] = odict([
                    ("numFrames", node.data.numFrames),
                    ("boneTableOffset", node.data.boneTableOffset),
                    ("animDataOffset", node.data.animDataOffset),
                ])

            elif isinstance(node.data, ShareJoint):
                node_json["data"] = odict([
                    ("JOBJ", node.skeleton),
                ])

            file_json["nodes"].append(node_json)
        return file_json


def main():
    parser = argparse.ArgumentParser(description='Dump Melee .dat files to JSON')
    parser.add_argument('datfile', help='The .dat file')
    parser.add_argument("outfile", help="Path to output JSON file.")
    parser.add_argument("-a", "--animfile", default=None,
                        help="Path to the corresponding animation file. If nothing is given an Pl**AJ.dat file will be looked for next to the PJ**.dat (the input)")
    parser.add_argument("--dumpanims", default=False, action="store_true",
                        help="Dumps animation files from the Pl**AJ.dat to separate files (per subaction)")
    parser.add_argument("--animpath", default="animationFiles",
                        help="Directory to where the animations from Pl**AJ.dat should be dumped to.")
    parser.add_argument("--time", default=False, action="store_true",
                        help="Times how long the dumping took. Mainly for optimization.")
    args = parser.parse_args()

    startTime = time.time()

    with open(args.datfile, "rb") as f:
        fileData = f.read()

    if args.animfile:
        ajFilePath = args.animfile
    else:
        ajFilePath = os.path.splitext(args.datfile)[0] + "AJ.dat"

    if os.path.isfile(ajFilePath):
        with open(ajFilePath, "rb") as f:
            animFileData = f.read()
    else:
        print("Pl**AJ.dat file not found in '{}'".format(ajFilePath))
        print("You can pass --animfile to pass the path to the AJ file directly")
        animFileData = None

    file = DatFile(fileData, animFileData)

    # Dump Anims
    if args.dumpanims:
        assert animFileData
        assert file.rootNodes[0].name.startswith(b"ftData")
        os.makedirs(args.animpath, exist_ok=True)
        for i, subact in enumerate(file.rootNodes[0].data.subactions):
            name = str(i)
            if len(subact.name) > 0:
                name += " - " + subact.shortName.decode("utf-8")
            with open(os.path.join(args.animpath, "{}.dat".format(name)), "wb") as f:
                if subact.animationSize > 0:
                    f.write(subact.animationData)

    # Save to JSON
    print("Saving to file {}..".format(args.outfile))
    with open(args.outfile, "w") as f:
        dictData = file.toJsonDict()
        dictData["sourceFile"] = os.path.basename(args.datfile)
        dictData.move_to_end("sourceFile", last=False)
        json.dump(dictData, f, indent=4)

    if args.time:
        print("Duration: {}s".format(time.time() - startTime))


if __name__ == "__main__":
    main()
