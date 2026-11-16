"""Interactive desktop integration check. Opens two local Tkinter clients."""
import json
import socket
import time
import tkinter as tk
from pathlib import Path
from chat_app import ChatApp


def free_port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p


def main():
    root=tk.Tk(); other=tk.Tk()
    a=ChatApp(root,tcp_port=free_port(),discovery_port=5099,preset_name='Lucy')
    b=ChatApp(other,tcp_port=free_port(),discovery_port=5099,preset_name='David')
    failures=[]
    result={}; started=time.monotonic(); phase=0
    assets=Path('reports/assets'); assets.mkdir(parents=True,exist_ok=True)
    def capture(name):
        from PIL import ImageGrab
        root.lift(); root.update_idletasks()
        x,y=root.winfo_rootx(),root.winfo_rooty()
        try:
            ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height())).save(assets/name)
        except Exception as exc:
            result['screenshot_capture'] = str(exc)
    def check():
        nonlocal phase
        try:
            if time.monotonic()-started>25:
                raise AssertionError('GUI check timed out')
            if phase==0:
                assert a.setup_name_var.get()=='Lucy'
                a._setup_complete(); assert a.setup_error_label.cget('text')
                capture('setup.png')
                a._toggle_password_visibility(); assert a.setup_pass_entry.cget('show') == ''
                a._toggle_password_visibility(); assert a.setup_pass_entry.cget('show') == '█'
                for app in (a,b):
                    app.setup_pass_var.set('night-city-private-passphrase');app._setup_complete()
                result['setup_validation']=True
                result['composer_disabled_before_verification']=a.msg_entry.cget('state')=='disabled'
                phase=1
            elif phase==1 and time.monotonic()-started>4:
                result['automatic_discovery']=any(p.port==b.tcp_port for p in a.peer_manager.all_peers()) and any(p.port==a.tcp_port for p in b.peer_manager.all_peers())
                a.direct_var.set(f'127.0.0.1:{b.tcp_port}');a._on_direct();phase=2
            elif phase==2 and a._state==b._state=='connected':
                a.msg_var.set('Night City, channel verified.');a._on_send()
                b.msg_var.set('Received. The signal is clear.');b._on_send();phase=3
            elif phase==3 and a._pkt_count==b._pkt_count==2:
                result['bidirectional_gui_chat']=True
                root.geometry('940x760+20+40');root.update_idletasks()
                result['minimum_size_composer_visible']=a.msg_entry.winfo_viewable()==1
                root.geometry('1100x820+20+40');root.update_idletasks();capture('chat.png')
                a._on_disconnect();phase=4
            elif phase==4 and b._state=='disconnected':
                result['disconnect_resets_composer']=a.msg_entry.cget('state')==b.msg_entry.cget('state')=='disabled'
                a._on_direct();phase=5
            elif phase==5 and a._state==b._state=='connected':
                result['reconnect']=True
                a._on_disconnect(); phase=6
            elif phase==6 and b._state=='disconnected':
                a.password='different-password';a._on_direct();phase=7
            elif phase==7 and a._state==b._state=='disconnected':
                result['wrong_password_rejected']=True
                result['elapsed_seconds']=round(time.monotonic()-started,2)
                Path('reports/gui_checks.json').write_text(json.dumps(result,indent=2))
                print(json.dumps(result,indent=2),flush=True)
                b._on_close();a._on_close();return
            root.after(100,check)
        except Exception:
            failures.append(True)
            import traceback;traceback.print_exc()
            Path('reports/gui_checks.json').write_text(json.dumps(result,indent=2))
            b._on_close();a._on_close();raise
    root.after(400,check); root.mainloop()
    if failures:
        raise SystemExit(1)

if __name__=='__main__':main()
