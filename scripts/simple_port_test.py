#!/usr/bin/env python3
"""
簡単なポート占有テスト
ポート8000を占有して、自動モザエセが8080を使用することを確認
"""

import socket
import time

def occupy_port_8000():
    """ポート8000を占有"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', 8000))
        sock.listen(1)
        
        print("🔒 ポート8000を占有しました")
        print("📋 この状態で自動モザエセのDiscord認証をテストしてください")
        print("⭐ 期待される動作: ポート8080が使用される")
        print("⏹️  Ctrl+C で停止します")
        
        # 簡単なHTTPサーバーのような動作
        while True:
            try:
                conn, addr = sock.accept()
                print(f"⚠️  ポート8000への接続を受信: {addr}")
                # 404レスポンスを返す
                response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
                conn.send(response)
                conn.close()
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
                
    except OSError as e:
        print(f"❌ ポート8000の占有に失敗: {e}")
        print("ポート8000は既に使用中の可能性があります")
    except KeyboardInterrupt:
        print("\n🛑 ポート占有を停止します")
    finally:
        try:
            sock.close()
            print("✅ ポート8000を解放しました")
        except:
            pass

if __name__ == "__main__":
    print("🧪 ポート8000占有テストツール")
    print("=" * 40)
    occupy_port_8000()
