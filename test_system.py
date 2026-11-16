"""Headless regression checks; run with python -m unittest -v test_system."""
import json
import socket
import struct
import threading
import time
import unittest
from encryption import EncryptionManager
from network import ChatConnection, TCPListener, MAX_FRAME_SIZE
from session import SecureSession


def wait_for(predicate, timeout=4):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return True
        time.sleep(.01)
    return False


class EncryptionTests(unittest.TestCase):
    def test_shared_salt_unicode_and_tampering(self):
        a, b = EncryptionManager(), EncryptionManager()
        a.set_password('private phrase'); b.set_password('private phrase', a.get_salt())
        token = a.encrypt_message('Hello 🌃 नमस्ते')
        self.assertEqual(b.decrypt_message(token), 'Hello 🌃 नमस्ते')
        self.assertIsNone(b.try_decrypt(token[:-5] + b'xxxxx'))
        b.set_password('wrong', a.get_salt())
        self.assertIsNone(b.try_decrypt(token))


class TransportTests(unittest.TestCase):
    def test_fragmented_frames_and_disconnect_once(self):
        left, right = socket.socketpair(); received=[]; closed=[]
        c=ChatConnection(lambda *args: received.append(args),lambda: closed.append(True)); c.accept(left)
        payload=json.dumps({'type':'chat','data':{'cipher':'abc'}}).encode()
        frame=struct.pack('!I',len(payload))+payload
        for byte in frame:
            right.sendall(bytes([byte]))
        self.assertTrue(wait_for(lambda: received))
        self.assertEqual(received[0],('chat',{'cipher':'abc'}))
        right.close(); self.assertTrue(wait_for(lambda: closed)); c.close()
        self.assertEqual(len(closed),1)

    def test_invalid_frames_close_cleanly(self):
        for payload in [b'not json', b'[]', b'{"type":"chat","data":[]}', None]:
            with self.subTest(payload=payload):
                left,right=socket.socketpair(); closed=[]
                c=ChatConnection(on_disconnect=lambda:closed.append(True)); c.accept(left)
                right.sendall(struct.pack('!I',len(payload) if payload else MAX_FRAME_SIZE+1)+(payload or b''))
                self.assertTrue(wait_for(lambda:closed)); right.close(); c.close()

    def test_occupied_listener_port(self):
        first=TCPListener(0,lambda s,a:s.close()); first.start()
        port=first._server.getsockname()[1]
        second=TCPListener(port,lambda s,a:s.close())
        try:
            with self.assertRaises(OSError): second.start()
        finally:
            first.stop(); second.stop()


class SessionTests(unittest.TestCase):
    def pair(self, password='secret'):
        left,right=socket.socketpair(); events_a=[]; events_b=[]
        a=SecureSession('secret','Alice',lambda *e:events_a.append(e))
        b=SecureSession(password,'Bob',lambda *e:events_b.append(e))
        self.addCleanup(a.close); self.addCleanup(b.close)
        ta=threading.Thread(target=a.start,kwargs={'client':left});tb=threading.Thread(target=b.start,kwargs={'client':right})
        ta.start();tb.start();ta.join();tb.join()
        return a,b,events_a,events_b

    def test_bidirectional_chat_and_reconnect(self):
        for _ in range(3):
            a,b,ea,eb=self.pair()
            self.assertTrue(wait_for(lambda:a.ready and b.ready))
            self.assertTrue(a.send('Hello 🌃')); self.assertTrue(b.send('Reply नमस्ते'))
            self.assertTrue(wait_for(lambda:any(e[0]=='message' for e in ea) and any(e[0]=='message' for e in eb)))
            self.assertIn(('message',('Alice','Hello 🌃')),eb)
            self.assertIn(('message',('Bob','Reply नमस्ते')),ea)
            a.close(); self.assertTrue(wait_for(lambda:b.closed));b.close()

    def test_wrong_password_never_ready(self):
        a,b,ea,eb=self.pair('wrong')
        self.assertTrue(wait_for(lambda:a.closed and b.closed))
        self.assertFalse(a.ready or b.ready)
        self.assertFalse(any(e[0]=='ready' for e in ea+eb))

    def test_handshake_timeout(self):
        left,right=socket.socketpair(); events=[]
        a=SecureSession('secret','Alice',lambda *e:events.append(e),timeout=.15)
        self.addCleanup(right.close);self.addCleanup(a.close)
        a.start(client=left)
        self.assertTrue(wait_for(lambda:a.closed))
        self.assertTrue(any('timed out' in str(e) for e in events))

    def test_reflected_or_incompatible_hello_rejected(self):
        for version in (1, 2):
            with self.subTest(version=version):
                left,right=socket.socketpair();events=[]
                a=SecureSession('secret','Alice',lambda *e:events.append(e))
                self.addCleanup(a.close);self.addCleanup(right.close)
                a.start(client=left)
                payload=json.dumps({'type':'hello','data':{
                    'version':version,'name':'Mirror','salt':a.cipher.get_salt().hex(),
                    'challenge':a.challenge}}).encode()
                right.sendall(struct.pack('!I',len(payload))+payload)
                self.assertTrue(wait_for(lambda:a.closed))
                self.assertFalse(a.ready)
                self.assertFalse(any(e[0]=='ready' for e in events))

    def test_refused_connection(self):
        s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
        events=[];a=SecureSession('secret','Alice',lambda *e:events.append(e));self.addCleanup(a.close)
        a.start('127.0.0.1',port)
        self.assertTrue(a.closed);self.assertEqual(events[0][0],'error')

if __name__=='__main__': unittest.main()
