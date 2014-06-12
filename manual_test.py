import asyncio
import selectors

from argparse import ArgumentParser
from functools import partial
from logging.config import dictConfig
from sys import stdout

from rfxcom import protocol
from rfxcom.transport import AsyncioTransport
from tests.stub import StubSerial, StubbedDefaultSelector

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)-8s %(name)-35s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': stdout,
            'formatter': 'standard'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': '/tmp/rfxcom.log',
            'maxBytes': 10 * 1024 * 1024,
        },
    },
    'loggers': {
        'rfxcom': {
            'handlers': ['console', 'file', ],
            'propagate': True,
            'level': 'DEBUG',
        }
    },
}


def status_handler(packet):
    return


def elec_handler(packet):
    print(packet)


def temp_humidity_handler(packet):
    return


def default_callback(packet):
    print("???? :", packet)


def write(rfxcom):
    print("WRITE RFXCOM")
    return


def main():

    dictConfig(LOGGING)


    parser = ArgumentParser()
    parser.add_argument('device')
    args = parser.parse_args()

    if args.device == 'stub':
        args.device = StubSerial()
        args.device.push_readable_data(b'\x123456')
        args.device.push_readable_data(b'\x7890')
        selectors.DefaultSelector = StubbedDefaultSelector

    loop = asyncio.get_event_loop()

    if isinstance(args.device, StubSerial):
        loop._selector.registerStub(args.device)

    try:
        rfxcom = AsyncioTransport(args.device, loop, callbacks={
            protocol.Status: status_handler,
            protocol.Elec: elec_handler,
            protocol.TempHumidity: temp_humidity_handler,
            '*': default_callback,
        })
        loop.call_later(2, partial(write, rfxcom))
        loop.run_forever()
    finally:
        print("Pending tasks at exit: %s" % asyncio.Task.all_tasks(loop))
        loop.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
