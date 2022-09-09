import asyncio
import logging
import os.path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pyzusi3.messagecoders import MessageDecoder, encode_obj
from pyzusi3 import messages
from pyzusi3.nodes import AsyncStreamDecoder

ZUSI_IP = "127.0.0.1"
ZUSI_PORT = "1436"

log = logging.getLogger("ZusiDemo")
logging.basicConfig(level=logging.WARNING)

async def decode_bytes(stream_bytes):
    decoder = AsyncStreamDecoder()
    decoded_tree = await decoder.decode(stream_bytes)
    messagedecoder = MessageDecoder()
    decoded_messages = messagedecoder.parse(decoded_tree)  
    return decoded_messages

async def zusitalk(ip, port):
    log.info("Connecting to Zusi3")
    reader, writer = await asyncio.open_connection(
        ip, port)

    log.info("Sending HELLO message")
    hello_msg = messages.HELLO(2, messages.ClientTyp.FAHRPULT, "Schlumpfpult", "1.0")
    log.debug(hello_msg)
    writer.write(encode_obj(hello_msg).encode())

    log.info("Waiting for response")
    basemessage, submessages = await decode_bytes(reader)
    log.debug(basemessage)
    if not (isinstance(basemessage, messages.ACK_HELLO) and basemessage.status == 0):
        log.error("Zusi did not report success for HELLO")
        return

    log.info("Request train speed and emer brake status")
    need_msg = messages.NEEDED_DATA([messages.FAHRPULT_ANZEIGEN.GESCHWINDIGKEIT_ABSOLUT, messages.FAHRPULT_ANZEIGEN.STATUS_NOTBREMSSYSTEM])
    writer.write(encode_obj(need_msg).encode())
    basemessage, submessages = await decode_bytes(reader)
    log.debug(basemessage)
    if not (isinstance(basemessage, messages.ACK_NEEDED_DATA) and basemessage.status == 0):
        log.error("Zusi did not report success for HELLO")

    try:
        while True:
            basemessage, submessages = await decode_bytes(reader)
            if isinstance(basemessage, messages.DATA_FTD) and basemessage.geschwindigkeit_absolut is not None:
                log.warning("Got new speed info: %s" % str(basemessage.geschwindigkeit_absolut))
            for submessage in submessages:
                if isinstance(submessage, messages.STATUS_NOTBREMSSYSTEM):
                    log.warning("New state for emer brakes: %s" % str(submessage))
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        pass
    log.info("Disconnecting")
    writer.close()

asyncio.run(zusitalk(ZUSI_IP, ZUSI_PORT))
