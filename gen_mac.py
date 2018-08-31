#!/usr/bin/env python

from random import randint

print(':'.join(map(lambda x: '%02x' % x, [ 0x52, 0x54, 0x00, randint(0, 255), randint(0, 255), randint(0, 255) ])))
