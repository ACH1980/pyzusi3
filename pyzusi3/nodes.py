from enum import Enum
import struct
import logging

from pyzusi3.exceptions import DecodeValueError, EncodingValueError, MissingBytesDecodeError, MissingContentTypeError

class ContentType(Enum):
    BYTE = 0
    SHORTINT = 1
    WORD = 2
    SMALLINT = 3
    INTEGER = 4
    CARDINAL = 5
    INTEGER64BIT = 6
    SINGLE = 7
    DOUBLE = 8
    STRING = 9
    FILE = 10
    RAW = 11 # same as file but used to indicate non-decoded content


class BasicNode:
    def __init__(self, id=None, content=None, contenttype=None, children=None, parent_node=None) -> None:
        self.id = id
        self.content = content
        self.contenttype = contenttype
        if children is not None:
            self.children = children
        else:
            self.children = []
        self.parent_node = parent_node

    def __eq__(self, other):
        return self.id == other.id and self.content == other.content and self.contenttype == other.contenttype and self.children == other.children

    def __repr__(self):
        return "<%s id=%s content=%s contenttype=%s parent_node=%s children=%s>" % (self.__class__.__name__, self.id, self.content, self.contenttype, self.parent_node, self.children)

    def _encodecontent(self):
        result = b''
        if self.contenttype is None:
            raise MissingContentTypeError("No contenttype has been given to encode to")
        if self.contenttype == ContentType.BYTE:
            try:
                if not 0 <= self.content <= 255:
                    raise EncodingValueError("Content %s exceeds limits of 0-255 for a byte")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range 0-255" % str(self.content))
            result += self.content.to_bytes(1, byteorder='little')
        elif self.contenttype == ContentType.SHORTINT:
            try:
                if not -128 <= self.content <= 127:
                    raise EncodingValueError("Content %s exceeds limits of -128 to 127 for a short int")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range -128 to 127" % str(self.content))
            result += self.content.to_bytes(1, byteorder='little')
        elif self.contenttype == ContentType.WORD:
            try:
                if not 0 <= self.content <= 65535:
                    raise EncodingValueError("Content %s exceeds limits of 0-65535 for a word")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range 0-65535" % str(self.content))
            result += self.content.to_bytes(2, byteorder='little')
        elif self.contenttype == ContentType.SMALLINT:
            try:
                if not -32768 <= self.content <= 32767:
                    raise EncodingValueError("Content %s exceeds limits of -32768 to 32767 for a small int")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range -32768 to 32767" % str(self.content))
            result += self.content.to_bytes(2, byteorder='little')
        elif self.contenttype == ContentType.INTEGER:
            try:
                if not -2147483648 <= self.content <= 2147483647:
                    raise EncodingValueError("Content %s exceeds limits of -2147483648 to 2147483647 for an int")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range -2147483648 to 2147483647" % str(self.content))
            result += self.content.to_bytes(4, byteorder='little')
        elif self.contenttype == ContentType.CARDINAL:
            try:
                if not 0 <= self.content <= 4294967295:
                    raise EncodingValueError("Content %s exceeds limits of 0 to 4294967295 for a cardinal")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range 0 to 4294967295" % str(self.content))
            result += self.content.to_bytes(4, byteorder='little')
        elif self.contenttype == ContentType.INTEGER64BIT:
            try:
                if not -9223372036854775808 <= self.content <= 9223372036854775807:
                    raise EncodingValueError("Content %s exceeds limits of -9223372036854775808 to 9223372036854775807 for an int64")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range -9223372036854775808 to 9223372036854775807" % str(self.content))
            result += self.content.to_bytes(8, byteorder='little')
        elif self.contenttype == ContentType.SINGLE:
            try:
                if not 1.5E-45 <= self.content <= 3.4E38:
                    raise EncodingValueError("Content %s exceeds limits of 1.5E-45 to 3.4E38 for a single")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range 1.5E-45 to 3.4E38" % str(self.content))
            try:
                result += struct.pack("<f", self.content)
            except OverflowError as e:
                raise EncodingValueError("Content %s cannot be encoded: %s" % str(e))
        elif self.contenttype == ContentType.DOUBLE:
            try:
                if not 5.0E-324 <= self.content <= 1.7E308:
                    raise EncodingValueError("Content %s exceeds limits of 5.0E-324 to 1.7E308 for a double")
            except TypeError:
                raise EncodingValueError("Content %s cannot be compared for range 5.0E-324 to 1.7E308" % str(self.content))
            try:
                result += struct.pack("<d", self.content)
            except OverflowError as e:
                raise EncodingValueError("Content %s cannot be encoded: %s" % str(e))
        elif self.contenttype == ContentType.STRING:
            try:
                result += self.content.encode("latin1")
            except UnicodeEncodeError:
                raise EncodingValueError("Content %s cannot be encoded: %s" % str(e))
        elif self.contenttype == ContentType.FILE or self.contenttype == ContentType.RAW:
            if not isinstance(self.content, bytes):
                raise EncodingValueError("Content is not in bytes format")
            result += self.content
        else:
            raise MissingContentTypeError("Content of type %s is unknown in the encoder. Programming bug?" % (self.contenttype))

        return result

    def encode(self):
        result = b''

        if self.children:
            result = (0).to_bytes(4, byteorder='little') # Node start

        if self.content is not None:
            bytecontent = self._encodecontent()
            bytecontentlength = 2 + len(bytecontent) # add 2 for the content id
            result += bytecontentlength.to_bytes(4, byteorder='little')
        if self.id is not None:
            result += self.id.to_bytes(2, byteorder='little')
        if self.content is not None:
            result += bytecontent

        if self.children:
            for child in self.children:
                result += child.encode()
            result += (0xffffffff).to_bytes(4, byteorder='little') # Node end
        
        return result


class DecoderState(Enum):
    RESET = 0
    CONTRENTLENGTH = 1
    NODEID = 2
    NODEIDFORCONTENT = 3
    CONTENT = 4


class StreamDecoder:
    def __init__(self) -> None:
        self.log = logging.getLogger("pyzusi3.node")

    def reset(self):
        self.log.info("Resetting state")
        self.state = DecoderState.RESET
        self.root_node = None
        self.current_node = None
        self.content_length = None

    def decode(self, bytecontent):
        if not isinstance(bytecontent, bytes):
            raise ValueError("Need bytes to decode, not %s" % type(bytecontent))
        self.log.info("Start decoding")
        self.reset()
        self.bytecontent = iter(bytecontent)
        self._decode()
        self.log.debug("Decoding result:")
        self.log.debug(repr(self.root_node))
        return self.root_node

    def _get_bytes(self, length):
        data = []
        for i in range(length):
            try:
                data.append(next(self.bytecontent))
            except StopIteration:
                raise MissingBytesDecodeError("Not enough bytes to get from datastream")
        return bytes(data)

    def _decode(self):
        previous_state = None
        while previous_state != self.state:
            self.log.debug("Current state: %s" % self.state)
            previous_state = self.state # healthcheck
            if self.state == DecoderState.RESET:
                incoming_bytes = self._get_bytes(4)
                if incoming_bytes != (0).to_bytes(4, byteorder='little'):
                    raise DecodeValueError("Expected 4 empty bytes for root node start but got %s" % incoming_bytes)
                self.root_node = self.current_node = BasicNode()
                self.log.debug("Created new node")
                self.state = DecoderState.NODEID
            elif self.state == DecoderState.NODEID or self.state == DecoderState.NODEIDFORCONTENT:
                incoming_bytes = self._get_bytes(2)
                self.current_node.id = struct.unpack("<H", incoming_bytes)[0]
                self.log.debug("Set node id to %s" % self.current_node.id)
                if self.state == DecoderState.NODEIDFORCONTENT:
                    self.state = DecoderState.CONTENT
                else:
                    self.state = DecoderState.CONTRENTLENGTH
            elif self.state == DecoderState.CONTRENTLENGTH:
                incoming_bytes = self._get_bytes(4)
                if incoming_bytes == (0xffffffff).to_bytes(4, byteorder='little'):
                    # marks end of nodetree
                    self.log.debug("Finished current node")
                    self.current_node = self.current_node.parent_node
                    self.state = DecoderState.CONTRENTLENGTH
                    if self.current_node == self.root_node:
                        return
                    continue
                self.log.debug("Creating new child node")
                new_node = BasicNode(parent_node=self.current_node)
                self.current_node.children.append(new_node)
                self.current_node = new_node

                content_length = struct.unpack("<I", incoming_bytes)[0]
                if content_length == 0:
                    # just subnodes, possibly with children themselves
                    self.state = DecoderState.NODEID
                    self.log.debug("No content, just setting id afterwards")
                else:
                    # real content follows after id
                    self.content_length = struct.unpack("<I", incoming_bytes)[0] - 2
                    self.log.debug("Setting id and adding content with length %s to node" % self.content_length)
                    self.state = DecoderState.NODEIDFORCONTENT
            elif self.state == DecoderState.CONTENT:
                self.current_node.content = self._get_bytes(self.content_length)
                self.current_node.contenttype = ContentType.RAW
                self.log.debug("Got content %s" % self.current_node.content)
                self.current_node = self.current_node.parent_node
                self.state = DecoderState.CONTRENTLENGTH
        if self.current_node != self.root_node:
            raise DecodeValueError("Not all nodes have been closed, data incomplete")