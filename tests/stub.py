""""Some Stub classes to improve testing"""

import queue
import selectors


class StubbedDefaultSelector(selectors.DefaultSelector):
    """Make StubSerial class work with selectors.DefaultSelector

    selectors.DefaultSelector is choosen automatically from a set of different
    impementations. This class takes the choosen implementation and extends it
    so that when a StubSerial instance has something to read or available to
    write, it will notify the main loop.

    To have it work:

    # before calling loop.get_event_loop() the first time, instantiating a new
    # loop.
    selectors.DefaultSelector = StubbedDefaultSelector
    # eventually get the loop
    loop = asyncio.get_event_loop()
    # the loop's selector should already be an instance of this class
    assert isinstance(loop._selector, StubbedDefaultSelector)
    # register a StubSerial instance to the loop's selector
    serial = StubSerial()
    loop._selector.registerStub(stub)
    """
    _stubs = {}

    def registerStub(self, stub):
        # let the StubbedSelector that we want to manage this stub
        # It's missing the key (None) as we can build it only when someone
        # registers for read or write to this stub/fileobj
        self._stubs[stub.fd] = stub, None

    def register(self, fileobj, events, data=None):
        if fileobj in self._stubs:
            # something is registering for read or write to this Stub
            stub, _ = self._stubs[fileobj]
            key = selectors.SelectorKey(stub, stub.fd, events, data)
            # update the key field in the stub register
            self._stubs[fileobj] = stub, key
            return self._stubs[fileobj]
        else:
            # not something we manage, pass up and behave as like the original
            # DefaultSelector
            return super().register(fileobj, events, data)

    def select(self, timeout=None):
        ret = []
        # for each registered Stub, build the appropriate response, if it can
        # read or write.
        for stub, key in self._stubs.values():
            events = 0
            if stub._can_read():
                events |= selectors.EVENT_READ
            if stub._can_write():
                events |= selectors.EVENT_WRITE

            ret.append((key, events))

        # Add our result for the Stub, if any, to the 'real' results the
        # DefaultSelector has
        return ret + super().select(timeout)


class StubSerial(object):
    """Stub for pyserial.Serial class
    """
    # fake file descriptor. It does not need to be valid, as long as it's a
    # positive integer. this fd it's actually never select()ed or poll()ed.
    fd = 1024
    _read_buffer = queue.Queue()
    _write_buffer = queue.Queue()
    _current_read_data = bytearray()

    def _can_read(self):
        """True if there is data to read()"""
        return not self._read_buffer.empty()

    def _can_write(self):
        """True if it's possible to write()"""
        return not self._write_buffer.full()

    def push_readable_data(self, d):
        """Push data into the read buffer

        so that the registered reader is able to access it
        """
        assert isinstance(d, (bytes, bytearray))
        self._read_buffer.put(d)

    def read(self, l=1):
        def to_read():
            """Do we need to read from the read buffer?
            """
            return (l - len(self._current_read_data)) > 0

        while to_read() and self._can_read():
            self._current_read_data.extend(self._read_buffer.get_nowait())

        data = self._current_read_data[:l]
        self._current_read_data = self._current_read_data[l:]

        return data

    def flushInput(self):
        pass

    def write(self, d):
        pass
