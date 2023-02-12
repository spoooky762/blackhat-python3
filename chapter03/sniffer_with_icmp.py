import socket
import os
import struct

from ctypes import *

# host için dinleme adresi
host = "192.168.0.187"


class IP(Structure):
    
    _fields_ = [
        ("ihl",           c_ubyte, 4),
        ("version",       c_ubyte, 4),
        ("tos",           c_ubyte),
        ("len",           c_ushort),
        ("id",            c_ushort),
        ("offset",        c_ushort),
        ("ttl",           c_ubyte),
        ("protocol_num",  c_ubyte),
        ("sum",           c_ushort),
        ("src",           c_uint32),
        ("dst",           c_uint32)
    ]

    def __new__(cls, socket_buffer=None):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):
        self.socket_buffer = socket_buffer

        # protokol sabitlerini adlarına eşler
        self.protocol_map = {1: "ICMP", 6: "TCP", 17: "UDP"}
        
        # insan tarafından okunabilen IP adresleri
        self.src_address = socket.inet_ntoa(struct.pack("@I", self.src))
        self.dst_address = socket.inet_ntoa(struct.pack("@I", self.dst))
    
        # insan tarafından okunabilen protokol
        try:
            self.protocol = self.protocol_map[self.protocol_num]
        except IndexError:
            self.protocol = str(self.protocol_num)


class ICMP(Structure):
    
    _fields_ = [
        ("type",         c_ubyte),
        ("code",         c_ubyte),
        ("checksum",     c_ushort),
        ("unused",       c_ushort),
        ("next_hop_mtu", c_ushort)
        ]
    
    def __new__(cls, socket_buffer):
        return cls.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer):
        self.socket_buffer = socket_buffer


# ham bir soket oluşturun ve onu ortak arayüze bağlayın
if os.name == "nt":
    socket_protocol = socket.IPPROTO_IP 
else:
    socket_protocol = socket.IPPROTO_ICMP
    
sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)

sniffer.bind((host, 0))

# yakalamaya dahil edilen IP başlıklarını istiyoruz
sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

# Windows kullanıyorsak promiscuous modunu kurmak için
# biraz ioctl göndermemiz gerekir
if os.name == "nt":
    sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)


try:
    while True:
        # tek bir pakette okumak
        raw_buffer = sniffer.recvfrom(65535)[0]
        
        # buffer'ın ilk 20 byte'ından bir IP başlığı oluşturun
        ip_header = IP(raw_buffer[:20])
      
        print("Protocol: %s %s -> %s" % (
            ip_header.protocol,
            ip_header.src_address,
            ip_header.dst_address)
              )

        # ICMP ise onu istiyoruz
        if ip_header.protocol == "ICMP":
            # ICMP paketimizin nerede başladığını hesaplayın
            offset = ip_header.ihl * 4
            buf = raw_buffer[offset:offset + sizeof(ICMP)]
            
            # ICMP yapımızı oluşturun
            icmp_header = ICMP(buf)
            
            print("ICMP -> Type: %d Code: %d" % (
                icmp_header.type,
                icmp_header.code)
                  )

# CTRL-C'yi işle
except KeyboardInterrupt:
    # Windows'taysak promiscuous modunu kapat
    if os.name == "nt":
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
