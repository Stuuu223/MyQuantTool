'''
Created on 2012-1-8

@author: ltdc
'''
# Echo client program
import socket
import struct
from . import RPCBase


class RPCClient:
    def __init__(self, host, port, timeout = 10, handler = None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, )
        self.socket.connect((host, port))
        if timeout > 0 :
            self.socket.settimeout(timeout)
        self.seq = 0
        self.handler = handler
         
    def request(self, func, params):
        self.seq += 1    
        d = {u"func":func, u"params":params}
        sendPack = RPCBase.TTPackage(self.seq, RPCBase.NET_CMD_RPC, d)
        datas = sendPack.encode()
        self.socket.sendall(datas)        
        while True:        
            recvPack = self._recvOnePackage()
            if recvPack.seq == self.seq :
                if recvPack.data["status"] == 0:
                    return recvPack.data[u"params"]
                else:
                    raise Exception(recvPack.data[u"params"])
            else:
                if self.handler:
                    self.handler.handle_sub_pack(recvPack.data[u"params"])
        
    def subscribe(self, func, params):
        self.seq += 1
        d = {u"func":func, u"params":params}
        sendPack = RPCBase.TTPackage(self.seq, RPCBase.NET_CMD_RPC, d)
        datas = sendPack.encode()
        self.socket.sendall(datas)
        return self.seq
        
    def recvPackages(self):
        while True:
            package = self._recvOnePackage()
            if self.handler:
                self.handler.handle_sub_pack(package.data[u"params"])
        
    def _recv_all(self, length):
        data = bytes()
        while len(data) < length:
            more = self.socket.recv(length - len(data))
            if not more:
                raise EOFError('socket closed %d bytes into a %d-byte message' % (len(data), length))
            data += more
        return data
        
    def _recvOnePackage(self):        
        strLen = self._recv_all(4)
        packLen,  = struct.unpack_from("!I", strLen, 0)
        strContent = self._recv_all(packLen - 4)        
        datas = strLen + strContent        
        package = RPCBase.TTPackage()
        package.decode(datas) 
        return package


def request(address, func, param, timeout = 10):
    pos = address.find(":")
    ip = address[0:pos]
    port = int(address[pos+1:])
    client = RPCClient(ip, port, timeout)
    return client.request(func, param)
