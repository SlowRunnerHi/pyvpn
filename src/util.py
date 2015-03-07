# encoding: utf-8
'''
Created on 2015年3月7日

@author: Sunday
'''
import fcntl  # @UnresolvedImport
import socket
import select
import os
import logging
import struct
import time
import sys
import argparse
logger = logging.getLogger('vpn')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)
PYVPN_VERSION = '0.1'

# find const values
# grep IFF_UP -rl /usr/include/
IFF_UP = 0x1
IFF_RUNNING = 0x40
IFNAMSIZ = 16
SIOCSIFADDR = 0x8916
SIOCSIFNETMASK = 0x891c
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
SIOCADDRT = 0x890B

RTF_UP = 0x0001
RTF_GATEWAY = 0x0002

AF_INET = socket.AF_INET


def to_int(s):
    try:
        return int(s)
    except ValueError as _unused:
        return None


class exp_none(object):
    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *args, **kwargs):
        try:
            return self.fn(*args, **kwargs)
        except Exception as e:
            logger.warn(e)
            return None


def make_tun():
    TUNSETIFF = 0x400454ca
    TUNSETOWNER = TUNSETIFF + 2
    IFF_TUN = 0x0001
    IFF_NO_PI = 0x1000

    # Open TUN device file.
    tun = open('/dev/net/tun', 'r+b')
    # Tall it we want a TUN device named tun0.
    ifr = struct.pack('16sH', 'tun%d', IFF_TUN | IFF_NO_PI)
    ret = fcntl.ioctl(tun, TUNSETIFF, ifr)
    dev, _ = struct.unpack('16sH', ret)
    dev = dev.strip()
    # Optionally, we want it be accessed by the normal user.
    fcntl.ioctl(tun, TUNSETOWNER, 1000)
    return dev, tun


@exp_none
def ifconfig(dev, ipaddr, netmask):
    # http://stackoverflow.com/questions/6652384/how-to-set-the-ip-address-from-c-in-linux
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_IP)
    AF_INET = socket.AF_INET
    fd = sock.fileno()
    addrbuf = struct.pack('BBBB', *[int(el) for el in ipaddr.split('.')])
    maskbuf = struct.pack('BBBB', *[int(el) for el in netmask.split('.')])
    sockaddr_mt = '16sHH4s'
    flags_mt = '16sH'
    # ADDR
    siocsifaddr = struct.pack(sockaddr_mt, dev, AF_INET, 0, addrbuf)
    fcntl.ioctl(fd, SIOCSIFADDR, siocsifaddr)
    # MASK
    siocsifnetmask = struct.pack(sockaddr_mt, dev, AF_INET, 0, maskbuf)
    fcntl.ioctl(fd, SIOCSIFNETMASK, siocsifnetmask)
    # ifconfig tun0 up
    ifr2 = struct.pack(flags_mt, dev, 0)
    ifr_ret = fcntl.ioctl(fd, SIOCGIFFLAGS, ifr2)
    cur_flags = struct.unpack(flags_mt, ifr_ret)[1]
    flags = cur_flags | (IFF_UP | IFF_RUNNING)
    ifr_ret = struct.pack(flags_mt, dev, flags)
    ifr_ret = fcntl.ioctl(fd, SIOCSIFFLAGS, ifr_ret)
    return 0


@exp_none
def add_route(dest, mask, gw):
    # sudo strace route add -net 192.168.0.0/24 gw 192.168.10.1
    # ioctl(3, SIOCADDRT, ifr)
    # /usr/include/net/route.h
    pad = '\x00' * 8
    inet_aton = socket.inet_aton
    sockaddr_in_fmt = 'hH4s8s'
    rtentry_fmt = 'L16s16s16sH38s'
    dst = struct.pack(sockaddr_in_fmt, AF_INET, 0, inet_aton(dest), pad)
    next_gw = struct.pack(sockaddr_in_fmt, AF_INET, 0, inet_aton(gw), pad)
    netmask = struct.pack(sockaddr_in_fmt, AF_INET, 0, inet_aton(mask), pad)
    rt_flags = RTF_UP | RTF_GATEWAY
    rtentry = struct.pack(rtentry_fmt,
                          0, dst, next_gw, netmask, rt_flags, '\x00' * 38)
    sock = socket.socket(AF_INET, socket.SOCK_DGRAM, 0)
    fcntl.ioctl(sock.fileno(), SIOCADDRT, rtentry)
    return 0


def enable_tcp_forward():
    logger.info(u'Set ip_forward=1')
    with open('/proc/sys/net/ipv4/ip_forward', 'wb+') as f1:
        f1.seek(0)
        f1.write('1')


__all__ = ['to_int', 'exp_none', 'make_tun',
           'ifconfig', 'add_route', 'enable_tcp_forward']
