"""
rfxcom.transport.asyncio
========================

"""

from rfxcom.transport.base import BaseTransport
from rfxcom.protocol import RESET_PACKET, STATUS_PACKET, MODE_PACKET


class AsyncioTransport(BaseTransport):

    def __init__(self, device, loop, callback=None, callbacks=None,
                 SerialClass=None):

        super().__init__(device, callback=callback, callbacks=callbacks,
                         SerialClass=SerialClass)

        self.loop = loop
        self.write_queue = []

        self.log.info("Attaching writer for setup.")
        loop.add_writer(self.dev.fd, self.setup)

    def setup(self):
        """Performs the RFXtrx initialisation protocol.

        Currently this is the rough workflow of the interactions with the
        RFXtrx. We also do a few extra things - flush the buffer, and attach
        readers/writers to the asyncio loop.

        1. Write a RESET packet (write all zeros)
        2. Wait at least 50ms and less than 9000ms
        3. Write the STATUS packet to verify the device is up.
        4. Receive status response
        5. Write the MODE packet to enable or disabled the required protocols.
        """

        self.log.info("Removing setup writer.")
        self.loop.remove_writer(self.dev.fd)

        self.log.info("Adding reader to prepare to receive.")
        self.loop.add_reader(self.dev.fd, self.read)

        self.log.info("Flushing the RFXtrx buffer.")
        self.dev.flushInput()

        self.log.info("Writing the reset packet to the RFXtrx. (blocking)")
        super().write(RESET_PACKET)

        self.log.info("Write the status packet in 0.1 seconds. (blocking)")
        self.loop.call_later(0.1, super().write, STATUS_PACKET)

        self.log.info("Adding the queued writer in 0.2 seconds.")
        self.loop.call_later(
            0.2, self.loop.add_writer, self.dev.fd, self._writer)

        self.log.info("Adding mode packet to the write queue.")
        self.write(MODE_PACKET)

    def _writer(self):
        """We have been called to write! Take the oldest item off the queue
        and use the write method on BaseTransport.
        """
        l = len(self.write_queue)

        if l > 0:
            self.log.debug("Serving from write queue (length %s)" % l)
            super().write(self.write_queue.pop(0))

    def write(self, data):
        """Add a data packet to the write queue. In this case, its a simple
        list. which is then consumed. This method is as light as possible.
        """
        self.write_queue.append(data)

    def do_callback(self, pkt):
        """Add the callback to the event loop, we use call soon because we just
        want it to be called at some point, but don't care when particularly.
        """
        callback, parser = self.get_callback_parser(pkt)
        self.loop.call_soon(callback, parser)

    def read(self):
        """We have been called to read! As a consumer, continue to read for
        the length of the packet and then pass to the callback.
        """

        data = self.dev.read()

        if len(data) == 0:
            self.log.warning("READ : Nothing received")
            return

        if data == b'\x00':
            self.log.warning("READ : Empty packet (Got \\x00)")
            return

        pkt = bytearray(data)
        data = self.dev.read(pkt[0])
        pkt.extend(bytearray(data))

        self.log.info("READ : %s" % self.format_packet(pkt))
        self.do_callback(pkt)
        return pkt
